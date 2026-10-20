# rag/views.py
import logging
import re
import unicodedata

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from conocimiento.models import BaseConocimiento
from .models import ConsultaFallida
from .retriever import recuperar_cursos
from .serializers import ChatRequestSerializer
from .generator import generar_respuesta_ia

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración de caché
# ---------------------------------------------------------------------------
CONTEXTO_TTL = 30 * 60
MAX_CURSOS_SESION = 15
MAX_CURSOS_TARJETAS = 10
CACHE_PREFIX = "chat:contexto:"

# ---------------------------------------------------------------------------
# Palabras que indican seguimiento sobre el contexto anterior (Tipo B)
# ---------------------------------------------------------------------------
_REFERENCIAS_SEGUIMIENTO = (
    "ese curso", "esa formación", "esa formacion",
    "el curso anterior", "la formación anterior", "la formacion anterior",
    "ese de", "esa de",
    "cuánto dura", "cuanto dura", "duración", "duracion",
    "dónde se imparte", "donde se imparte",
    "cuándo empieza", "cuando empieza",
    "cómo me apunto", "como me apunto",
    "cómo me inscribo", "como me inscribo",
    "más información", "mas informacion",
    "más detalles", "mas detalles",
    "cuál es el precio", "cual es el precio",
    "es gratuito", "tiene coste", "cuánto cuesta", "cuanto cuesta",
    "para quién es", "para quien es",
    "qué requisitos", "que requisitos",
    "hay plazas", "quedan plazas",
    "dame información sobre ese", "dame informacion sobre ese",
    "cuéntame más", "cuentame mas",
    "más información sobre", "mas informacion sobre",
    "quiero más información", "quiero mas informacion",
    "me puedes dar más información", "me puedes dar mas informacion",
)

# ---------------------------------------------------------------------------
# Palabras que indican selección de un curso concreto (Tipo C)
# ---------------------------------------------------------------------------
_REFS_POSICION = re.compile(
    r"\b(?:el|la)\s+(primer[oa]?|segund[oa]?|tercer[oa]?|cuart[oa]?|quint[oa]?|1|2|3|4|5)\b",
    re.IGNORECASE,
)
_POSICION_MAP = {
    "primer": 0, "primero": 0, "primera": 0,
    "segund": 1, "segundo": 1, "segunda": 1,
    "tercer": 2, "tercero": 2, "tercera": 2,
    "cuarto": 3, "cuarta": 3,
    "quinto": 4, "quinta": 4,
    "1": 0, "2": 1, "3": 2, "4": 3, "5": 4,
}

_SELECCION_KEYWORDS = (
    "me interesa", "quiero ese", "quiero el", "quiero la",
    "elige ese", "selecciona ese", "dame ese", "dame el",
    "información sobre el", "informacion sobre el",
    "información sobre la", "informacion sobre la",
    "háblame del", "hablame del", "háblame de la", "hablame de la",
    "el primero", "el segundo", "el tercero", "el cuarto", "el quinto",
    "la primera", "la segunda", "la tercera", "la cuarta", "la quinta",
    "el 1", "el 2", "el 3", "el 4", "el 5",
)

_PREFIJO_CATALOGO = "consulta automatica"


# ---------------------------------------------------------------------------
# Helpers de normalización y caché
# ---------------------------------------------------------------------------
def _normalizar(texto: str) -> str:
    """Elimina acentos y convierte el texto a minúsculas."""
    if not texto:
        return ""
    return (
        unicodedata.normalize("NFD", str(texto))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def _cache_key(sesion_uuid: str) -> str:
    return f"{CACHE_PREFIX}{sesion_uuid}"


def _guardar_contexto(
    sesion_uuid: str,
    cursos: list,
    curso_seleccionado_pk=None,
) -> None:
    """Guarda los PK de los cursos mostrados y el curso seleccionado."""
    if not sesion_uuid:
        return

    ids = [curso.pk for curso in cursos[:MAX_CURSOS_SESION]]
    contexto = {
        "cursos_mostrados": ids,
        "curso_seleccionado": curso_seleccionado_pk,
    }
    cache.set(_cache_key(sesion_uuid), contexto, timeout=CONTEXTO_TTL)
    logger.debug(
        "[Chat] Contexto guardado | sesion=%s | mostrados=%s | seleccionado=%s",
        sesion_uuid, ids, curso_seleccionado_pk,
    )

def _cursos_para_respuesta(cursos: list) -> list:
    """
    Convierte los cursos del ORM en datos JSON para las tarjetas
    interactivas del widget.
    """
    campos = (
        "titulo",
        "url_oficial",
        "localidad",
        "provincia",
        "contenido",
        "objetivos",
        "competencias",
        "familia_profesional",
        "sector",
        "destinatarios",
        "colectivo",
        "requisitos",
        "certificado",
        "modalidad",
        "duracion",
        "precio",
        "fecha_inicio",
        "horario",
    )

    resultado = []

    for curso in cursos[:MAX_CURSOS_SESION]:
        ficha = {}

        for campo in campos:
            valor = getattr(curso, campo, None)

            if valor is None:
                ficha[campo] = ""
                continue

            texto = str(valor).strip()

            if texto.casefold() in {
                "",
                "n/d",
                "nd",
                "no disponible",
                "none",
                "null",
            }:
                texto = ""

            ficha[campo] = texto

        # Evitar enviar enlaces que no sean HTTP o HTTPS.
        url = ficha["url_oficial"]

        if url and not url.lower().startswith(("https://", "http://")):
            ficha["url_oficial"] = ""

        if not ficha["titulo"]:
            ficha["titulo"] = "Curso sin título identificado"

        resultado.append(ficha)

    return resultado

def _recuperar_contexto(sesion_uuid: str) -> dict:
    """Devuelve los cursos mostrados y el curso seleccionado desde caché."""
    vacio = {"cursos_mostrados": [], "curso_seleccionado": None}
    if not sesion_uuid:
        return vacio

    try:
        datos = cache.get(_cache_key(sesion_uuid))
    except Exception as exc:
        logger.error("[Chat] Error de caché al recuperar contexto: %s", exc)
        return vacio

    if not datos:
        return vacio

    ids = datos.get("cursos_mostrados", [])
    sel_pk = datos.get("curso_seleccionado")

    cursos = list(BaseConocimiento.objects.filter(activo=True, pk__in=ids))
    orden = {pk: i for i, pk in enumerate(ids)}
    cursos.sort(key=lambda curso: orden.get(curso.pk, len(ids)))

    seleccionado = next(
        (curso for curso in cursos if curso.pk == sel_pk),
        None,
    ) if sel_pk else None

    logger.debug(
        "[Chat] Contexto recuperado | sesion=%s | mostrados=%s | seleccionado=%s",
        sesion_uuid, [curso.pk for curso in cursos], sel_pk,
    )
    return {
        "cursos_mostrados": cursos,
        "curso_seleccionado": seleccionado,
    }


def _actualizar_seleccion(sesion_uuid: str, curso_seleccionado_pk) -> None:
    """Actualiza el curso seleccionado sin modificar la lista mostrada."""
    if not sesion_uuid:
        return

    try:
        datos = cache.get(_cache_key(sesion_uuid)) or {}
        datos["curso_seleccionado"] = curso_seleccionado_pk
        cache.set(_cache_key(sesion_uuid), datos, timeout=CONTEXTO_TTL)
        logger.debug(
            "[Chat] Selección actualizada | sesion=%s | seleccionado=%s",
            sesion_uuid, curso_seleccionado_pk,
        )
    except Exception as exc:
        logger.error("[Chat] Error de caché al actualizar selección: %s", exc)


def _serializar_curso(curso) -> dict:
    """Convierte una ficha ORM en datos seguros para las tarjetas del widget."""
    campos = (
        "titulo", "url_oficial", "localidad", "provincia", "contenido",
        "objetivos", "competencias", "familia_profesional", "sector",
        "destinatarios", "colectivo", "requisitos", "certificado",
        "modalidad", "duracion", "precio", "fecha_inicio", "horario",
    )
    vacios = {
        "", "n/d", "nd", "no disponible", "none", "null",
        "desconocido", "sin información", "sin informacion",
    }
    datos = {"id": getattr(curso, "pk", None)}

    for campo in campos:
        valor = getattr(curso, campo, None)
        texto = "" if valor is None else str(valor).strip()
        if texto.casefold() in vacios:
            texto = ""
        datos[campo] = texto

    # Solo devolvemos enlaces HTTP(S); el widget volverá a validarlos antes
    # de convertirlos en enlaces clicables.
    url = datos.get("url_oficial", "")
    if not url.lower().startswith(("https://", "http://")):
        datos["url_oficial"] = ""

    return datos


def _cursos_para_respuesta(cursos: list, limite: int = MAX_CURSOS_TARJETAS) -> list:
    """Serializa un conjunto de cursos aprovechables para el frontend."""
    salida = []
    vistos = set()

    for curso in cursos:
        pk = getattr(curso, "pk", None)
        if pk in vistos:
            continue
        vistos.add(pk)
        salida.append(_serializar_curso(curso))
        if len(salida) >= limite:
            break

    return salida


# ---------------------------------------------------------------------------
# Clasificación del mensaje
# ---------------------------------------------------------------------------
def _es_catalogo_automatico(pregunta: str) -> bool:
    """Detecta peticiones de catálogo, tanto internas como escritas por el usuario."""
    texto = _normalizar(" ".join((pregunta or "").casefold().split()))
    texto = re.sub(r"[¿?¡!.,;:]+", "", texto).strip()

    # Prefijo especial utilizado por el frontend.
    if texto.startswith(_normalizar(_PREFIJO_CATALOGO)):
        return True

    # Peticiones genéricas para mostrar el catálogo.
    patrones = (
        r"cuales cursos hay disponibles",
        r"cuales son los cursos disponibles",
        r"cuales son los cursos que hay",
        r"que cursos hay",
        r"que cursos hay disponibles",
        r"que cursos estan disponibles",
        r"lista de cursos",
        r"lista de cursos disponibles",
        r"mostrar cursos",
        r"mostrar cursos disponibles",
        r"ver cursos",
        r"ver cursos disponibles",
        r"catalogo",
        r"catalogo de cursos",
        r"cursos disponibles",
    )

    for patron in patrones:
        if texto == patron or re.fullmatch(
            re.escape(patron) + r" en [a-z ]+",
            texto,
        ):
            return True

    return False


def _es_seguimiento(pregunta: str) -> bool:
    """Detecta una pregunta breve sobre información vista anteriormente."""
    texto = (pregunta or "").strip().lower()
    if not texto:
        return False
    return any(ref in texto for ref in _REFERENCIAS_SEGUIMIENTO)


def _es_intencion_inscripcion(pregunta: str) -> bool:
    """Detecta intención de inscribirse, matricularse o reservar plaza."""
    texto = " ".join((pregunta or "").casefold().split())
    palabras_clave = (
        "inscrib", "inscripcion", "inscripción",
        "matricul", "matricula", "matrícula",
        "apuntar", "apuntarme", "reservar plaza",
        "reservar mi plaza", "solicitar plaza",
        "quiero hablar con un agente",
    )
    return any(palabra in texto for palabra in palabras_clave)


def _detectar_seleccion(pregunta: str, cursos_mostrados: list):
    """Resuelve una selección por número, ordinal, título o ubicación.

    Devuelve el curso seleccionado, None si una referencia explícita es
    inválida/ambigua, y False si el mensaje parece una consulta nueva.
    """
    texto = " ".join((pregunta or "").casefold().split())
    texto_norm = _normalizar(texto)

    if not cursos_mostrados:
        return False

    limite = min(10, len(cursos_mostrados))

    # Número aislado: se interpreta como número de curso porque las respuestas
    # de búsqueda se presentan como opciones numeradas.
    if re.fullmatch(r"(\d{1,2})[.!]?", texto):
        numero = int(re.fullmatch(r"(\d{1,2})[.!]?", texto).group(1))
        if 1 <= numero <= limite:
            return cursos_mostrados[numero - 1]
        return None

    # Frases: "el número 1", "número 1", "opción 2", "curso 3".
    m_numero = re.search(
        r"\b(?:el\s+)?(?:n[uú]mero|opci[oó]n|curso)\s*(?:n[ºo.]?\s*)?([1-9]|10)\b",
        texto,
        re.IGNORECASE,
    )
    if m_numero:
        numero = int(m_numero.group(1))
        if 1 <= numero <= limite:
            return cursos_mostrados[numero - 1]
        return None

    # Ordinales: "el primero", "la segunda", "el 2".
    m = _REFS_POSICION.search(texto)
    if m:
        token = m.group(1).lower()
        indice = _POSICION_MAP.get(token)
        if indice is not None and 0 <= indice < min(5, len(cursos_mostrados)):
            return cursos_mostrados[indice]
        return None

    palabras_ignoradas = {
        "curso", "cursos", "cefye", "el", "la", "los", "las",
        "de", "del", "en", "por", "para", "quiero", "busco",
        "interesa", "ese", "esa", "este", "esta", "más", "mas",
        "informacion", "información", "sobre", "dame", "me", "si",
        "detallada", "detallado", "detalle", "detalles", "imformacion",
    }
    palabras = [
        palabra
        for palabra in re.findall(r"\w+", texto_norm)
        if len(palabra) >= 3 and palabra not in palabras_ignoradas
    ]

    if palabras:
        candidatos = []
        for curso in cursos_mostrados[:MAX_CURSOS_SESION]:
            referencia = _normalizar(
                f"{getattr(curso, 'titulo', '')} "
                f"{getattr(curso, 'localidad', '') or ''} "
                f"{getattr(curso, 'provincia', '') or ''}"
            )
            if all(palabra in referencia for palabra in palabras):
                candidatos.append(curso)

        if len(candidatos) == 1:
            return candidatos[0]
        if len(candidatos) > 1:
            return None

    es_seleccion = any(
        palabra in texto
        for palabra in _SELECCION_KEYWORDS
    )
    if es_seleccion:
        return None

    return False


# ---------------------------------------------------------------------------
# Helpers de respuesta
# ---------------------------------------------------------------------------
def _registrar_fallo(pregunta: str, motivo: str) -> None:
    try:
        ConsultaFallida.objects.create(texto_consulta=pregunta, motivo_fallo=motivo)
    except Exception as db_exc:
        logger.error("[DB] Fallo al registrar ConsultaFallida: %s", db_exc)


def _respuesta_listado(resultados: list, filtros: dict) -> str:
    """Genera el mensaje introductorio del listado; las fichas van por JSON."""
    zona = filtros.get("provincia") or filtros.get("localidad") or "tu zona"
    return (
        f"He encontrado {len(resultados)} cursos disponibles en {zona}. "
        "Pulsa sobre el título de un curso para ver sus detalles."
    )


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def chat_ask_view(request):
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    pregunta = (
        serializer.validated_data.get("pregunta", "") or ""
    ).strip()

    filtros = dict(
        serializer.validated_data.get("filtros", {}) or {}
    )

    sesion_uuid = serializer.validated_data.get("sesion_uuid")

    if sesion_uuid:
        sesion_uuid = str(sesion_uuid)

    # Compatibilidad con clientes que envían provincia en la raíz.
    provincia_directa = serializer.validated_data.get("provincia")

    if provincia_directa and not filtros.get("provincia"):
        filtros["provincia"] = provincia_directa

    try:
        # ----------------------------------------------------------
        # 1. Catálogo automático solicitado por el frontend
        # ----------------------------------------------------------
        if _es_catalogo_automatico(pregunta):
            resultados = recuperar_cursos(
            "Consulta automatica de catálogo",
            filtros,
    )

            if not resultados:
                # Elimina el contexto anterior para no mostrar cursos
                # antiguos cuando no hay resultados para esta zona.
                _guardar_contexto(sesion_uuid, [], None)

                zona = (
                    filtros.get("provincia")
                    or filtros.get("localidad")
                    or "la zona seleccionada"
                )

                return Response({
                    "texto_respuesta": (
                        f"No he encontrado cursos disponibles en {zona} "
                        "con los criterios actuales. Puedes probar otra "
                        "provincia o solicitar ayuda de un asesor."
                    ),
                    "cursos": [],
                    "fallback_activado": True,
                    "requiere_accion_comercial": True,
                }, status=status.HTTP_200_OK)

            _guardar_contexto(sesion_uuid, resultados)

            zona = (
                filtros.get("provincia")
                or filtros.get("localidad")
                or "tu zona"
            )

            return Response({
                "texto_respuesta": (
                    f"He encontrado {len(resultados)} cursos disponibles "
                    f"en {zona}. Pulsa sobre un título para consultar "
                    "sus detalles."
                ),
                "cursos": _cursos_para_respuesta(resultados),
                "fallback_activado": False,
                "requiere_accion_comercial": False,
            }, status=status.HTTP_200_OK)

        # ----------------------------------------------------------
        # 2. Recuperar el contexto de la sesión
        # ----------------------------------------------------------
        contexto = _recuperar_contexto(sesion_uuid)

        cursos_mostrados = contexto["cursos_mostrados"]
        curso_seleccionado = contexto["curso_seleccionado"]

        # ----------------------------------------------------------
        # 3. Detectar selección por número, título u ordinal
        # ----------------------------------------------------------
        texto_normalizado = _normalizar(pregunta)
        texto_min = " ".join(pregunta.casefold().split())

        seleccion = None

        if cursos_mostrados:
            # Permite "1", "2.", "el número 1" o
            # "me interesa el número 1, dame información detallada".
            patron_numero = re.search(
                r"\b(?:numero|opcion)\s+([1-9]\d*)\b",
                texto_normalizado,
            )

            numero_aislado = re.fullmatch(
                r"(?:el\s+)?([1-9]\d*)[.!]?",
                texto_min,
            )

            numero = None

            if patron_numero:
                numero = int(patron_numero.group(1))
            elif numero_aislado:
                numero = int(numero_aislado.group(1))

            if numero is not None:
                # Los números corresponden al orden de la lista
                # de cursos guardada en la sesión.
                if 1 <= numero <= len(cursos_mostrados):
                    seleccion = cursos_mostrados[numero - 1]
                else:
                    seleccion = None
            else:
                seleccion = _detectar_seleccion(
                    pregunta,
                    cursos_mostrados,
                )
        else:
            seleccion = _detectar_seleccion(
                pregunta,
                cursos_mostrados,
            )

        if seleccion is False:
            # No conservar un curso seleccionado cuando se inicia
            # una búsqueda nueva.
            if (
                not _es_seguimiento(pregunta)
                and not _es_intencion_inscripcion(pregunta)
            ):
                curso_seleccionado = None

        elif seleccion is None and cursos_mostrados:
            titulos = "\n".join(
                f"{i}. {getattr(c, 'titulo', None) or 'Curso sin título identificado'} "
                f"({getattr(c, 'localidad', None) or getattr(c, 'provincia', None) or 'Ubicación no indicada'})"
                for i, c in enumerate(cursos_mostrados, start=1)
            )

            mensaje = (
                "No he podido identificar con seguridad el curso. "
                "Pulsa su título o indica el número que aparece en la lista.\n\n"
                f"{titulos}"
            )

            return Response({
                "texto_respuesta": mensaje,
                "fallback_activado": False,
                "requiere_accion_comercial": False,
            }, status=status.HTTP_200_OK)

        elif seleccion is not None:
            curso_seleccionado = seleccion

            _actualizar_seleccion(
                sesion_uuid,
                seleccion.pk,
            )

            logger.info(
                "[RAG] Curso seleccionado | sesion=%s | pk=%s | titulo=%r",
                sesion_uuid,
                seleccion.pk,
                seleccion.titulo,
            )

        # ----------------------------------------------------------
        # 4. Seguimiento sobre un curso o una lista anterior
        # ----------------------------------------------------------
        contexto_activo = (
            _es_seguimiento(pregunta)
            or _es_intencion_inscripcion(pregunta)
            or curso_seleccionado is not None
        )

        if contexto_activo:
            if curso_seleccionado is not None:
                resultados_ia = [curso_seleccionado]

                logger.info(
                    "[RAG] Seguimiento sobre curso seleccionado | "
                    "sesion=%s | pk=%s",
                    sesion_uuid,
                    curso_seleccionado.pk,
                )

            elif cursos_mostrados:
                resultados_ia = cursos_mostrados

                logger.info(
                    "[RAG] Seguimiento sobre lista | sesion=%s | n=%d",
                    sesion_uuid,
                    len(cursos_mostrados),
                )

            else:
                return Response({
                    "texto_respuesta": (
                        "No tengo cursos anteriores en el contexto "
                        "de esta conversación. Indícame qué formación "
                        "buscas para continuar."
                    ),
                    "fallback_activado": False,
                    "requiere_accion_comercial": False,
                }, status=status.HTTP_200_OK)

            # La inscripción facilita el enlace oficial y activa
            # el formulario para solicitar asistencia.
            if _es_intencion_inscripcion(pregunta):
                if curso_seleccionado is not None:
                    titulo = (
                        getattr(curso_seleccionado, "titulo", None)
                        or "el curso seleccionado"
                    )

                    url_oficial = (
                        getattr(curso_seleccionado, "url_oficial", None)
                        or ""
                    ).strip()

                    if url_oficial.lower().startswith(
                        ("https://", "http://")
                    ):
                        texto = (
                            f"Para consultar cómo inscribirte en {titulo}, "
                            "revisa la ficha oficial del curso:\n"
                            f"{url_oficial}"
                        )
                    else:
                        texto = (
                            f"No tengo un enlace oficial disponible para "
                            f"{titulo}. Puedes solicitar ayuda a CEFYE "
                            "para confirmar el procedimiento de inscripción."
                        )
                else:
                    opciones = "\n".join(
                        f"{i}. {c.titulo}"
                        for i, c in enumerate(cursos_mostrados, start=1)
                    )

                    texto = (
                        "¿En cuál de estos cursos quieres inscribirte?\n\n"
                        f"{opciones}"
                    )

                return Response({
                    "texto_respuesta": texto,
                    "fallback_activado": False,
                    "requiere_accion_comercial": True,
                }, status=status.HTTP_200_OK)

            # La IA responde a la pregunta usando solo el contexto
            # del curso seleccionado o de la lista recuperada.
            respuesta_ia = generar_respuesta_ia(
                pregunta,
                resultados_ia,
                es_seguimiento=True,
            )

            return Response({
                "texto_respuesta": respuesta_ia.get(
                    "texto_respuesta", ""
                ),
                "fallback_activado": respuesta_ia.get(
                    "fallback_activado", False
                ),
                "requiere_accion_comercial": respuesta_ia.get(
                    "requiere_accion_comercial", False
                ),
            }, status=status.HTTP_200_OK)

        # ----------------------------------------------------------
        # 5. Búsqueda nueva
        # ----------------------------------------------------------
        resultados = recuperar_cursos(pregunta, filtros)

        if not resultados:
            logger.info(
                "[RAG] Sin resultados para: %r | filtros=%s",
                pregunta,
                filtros,
            )

            _registrar_fallo(
                pregunta,
                "Sin resultados en retriever",
            )

            # No dejar seleccionado un curso de una búsqueda anterior.
            _guardar_contexto(sesion_uuid, [], None)

            return Response({
                "texto_respuesta": (
                    "No he encontrado formación relacionada con esa "
                    "consulta. Prueba con otra competencia, área "
                    "profesional o localidad."
                ),
                "cursos": [],
                "fallback_activado": False,
                "requiere_accion_comercial": False,
            }, status=status.HTTP_200_OK)

        # Guarda los cursos reales recuperados.
        _guardar_contexto(sesion_uuid, resultados)

        # Distinguir una búsqueda de cursos de una pregunta sobre
        # información específica de esos cursos.
        consulta_normalizada = _normalizar(pregunta)

        palabras_detalle = (
            "duracion",
            "cuanto dura",
            "modalidad",
            "requisitos",
            "certificado",
            "horario",
            "precio",
            "fecha de inicio",
            "cuando empieza",
            "inscripcion",
            "como me inscribo",
            "mas informacion",
            "informacion detallada",
            "mas detalles",
            "contenido del curso",
            "objetivos del curso",
        )

        solicita_detalle = any(
            patron in consulta_normalizada
            for patron in palabras_detalle
        )

        if solicita_detalle:
            respuesta_ia = generar_respuesta_ia(
                pregunta,
                resultados[:3],
                es_seguimiento=False,
            )

            texto_respuesta = respuesta_ia.get(
                "texto_respuesta", ""
            )

            fallback_activado = respuesta_ia.get(
                "fallback_activado", False
            )

            requiere_accion_comercial = respuesta_ia.get(
                "requiere_accion_comercial", False
            )

        else:
            # Las búsquedas temáticas se muestran desde PostgreSQL,
            # no como listas inventadas por el modelo generativo.
            texto_respuesta = (
                f"He encontrado {len(resultados)} cursos relacionados "
                "con tu consulta. Pulsa sobre un título para ver "
                "sus detalles."
            )

            fallback_activado = False
            requiere_accion_comercial = False

        return Response({
            "texto_respuesta": texto_respuesta,
            "cursos": _cursos_para_respuesta(resultados),
            "fallback_activado": fallback_activado,
            "requiere_accion_comercial": requiere_accion_comercial,
        }, status=status.HTTP_200_OK)

    except Exception as exc:
        logger.exception(
            "[RAG] Excepción interna procesando %r: %s",
            pregunta,
            exc,
        )

        _registrar_fallo(
            pregunta,
            f"Error Inferencia: {str(exc)}",
        )

        return Response({
            "error": (
                "El motor de inteligencia artificial no está disponible "
                "en este momento."
            )
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)