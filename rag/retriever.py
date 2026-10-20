import re
import logging

from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank

from conocimiento.models import BaseConocimiento
from rag.generator import _curso_aprovechable

logger = logging.getLogger(__name__)

UMBRAL_MINIMO = 0.01
NORMALIZACION_RANK = 1
MAX_LISTADO = 15

MAPA_LOCALIDADES_CYL = {
    "Ávila": [
        "Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda",
        "El Barco de Ávila", "Las Navas del Marqués",
    ],
    "Burgos": [
        "Burgos", "Miranda de Ebro", "Aranda de Duero",
        "Briviesca", "Medina de Pomar",
        "Villarcayo de Merindad de Castilla La Vieja",
    ],
    "León": [
        "León", "Leon", "León Capital", "Leon Capital",
        "León ciudad", "Ponferrada", "San Andrés del Rabanedo",
        "Villaquilambre", "Astorga", "La Bañeza", "Bembibre",
        "Valencia de Don Juan",
    ],
    "Palencia": [
        "Palencia", "Aguilar de Campoo", "Guardo",
        "Venta de Baños", "Villamuriel de Cerrato",
        "Herrera de Pisuerga",
    ],
    "Salamanca": [
        "Salamanca", "Béjar", "Ciudad Rodrigo",
        "Santa Marta de Tormes", "Carbajosa de la Sagrada",
        "Peñaranda de Bracamonte", "Guijuelo",
    ],
    "Segovia": [
        "Segovia", "Cuéllar", "El Espinar",
        "Real Sitio de San Ildefonso", "Palazuelos de Eresma",
        "Nava de la Asunción",
    ],
    "Soria": [
        "Soria", "Almazán",
        "El Burgo de Osma-Ciudad de Osma", "Golmayo",
        "San Esteban de Gormaz", "Ágreda",
    ],
    "Valladolid": [
        "Valladolid", "Laguna de Duero", "Medina del Campo",
        "Arroyo de la Encomienda", "Tordesillas",
        "Cistérniga", "Zaratán", "Simancas",
    ],
    "Zamora": [
        "Zamora", "Benavente", "Toro", "Morales del Vino",
        "Puebla de Sanabria", "Villaralbo",
    ],
}

# Normalización de vocales acentuadas y ñ.
TRANSLATION_TABLE = str.maketrans(
    "áéíóúñ",
    "aeioun",
)

PALABRAS_GENERICAS = {
    "formacion", "curso", "cursos", "en", "de", "del",
    "la", "el", "los", "las", "para", "por", "con",
    "sobre", "quiero", "busco", "hay", "tengo", "necesito",
    "dame", "un", "una", "y", "o", "que", "tienen",
    "teneis", "como", "donde", "cefye", "gratuita",
    "gratuito", "gratis",
}

PALABRAS_LISTADO = (
    "todos",
    "listar",
    "muestrame",
    "provincia",
    "listado",
)

_PREFIJOS_CONSULTA_AUTOMATICA = (
    "consulta automatica",
)


def _limpiar_texto(texto: str) -> str:
    """Normaliza texto para comparar términos sin distinguir acentos."""
    if not texto:
        return ""

    return texto.lower().translate(TRANSLATION_TABLE)

def _corregir_errores_comunes(texto: str) -> str:
    """Corrige erratas conocidas antes de buscar cursos."""
    correcciones = {
        r"\bofirmatica\b": "ofimática",
    }

    for patron, correccion in correcciones.items():
        texto = re.sub(
            patron,
            correccion,
            texto,
            flags=re.IGNORECASE,
        )

    return texto


def _es_consulta_automatica(preg_limpia: str) -> bool:
    """Detecta las consultas automáticas del catálogo."""
    if not preg_limpia.strip():
        return True

    return any(
        preg_limpia.startswith(prefijo)
        for prefijo in _PREFIJOS_CONSULTA_AUTOMATICA
    )


def _aparece(frase_limpia: str, texto_limpio: str) -> bool:
    """Comprueba que una localidad o provincia aparece como término completo."""
    return (
        re.search(
            rf"\b{re.escape(frase_limpia)}\b",
            texto_limpio,
        )
        is not None
    )


def _detectar_geografia(preg_limpia: str):
    """Detecta una provincia o localidad de Castilla y León."""
    for provincia, localidades in MAPA_LOCALIDADES_CYL.items():
        provincia_limpia = _limpiar_texto(provincia)

        if _aparece(provincia_limpia, preg_limpia):
            return provincia, None

        for localidad in localidades:
            localidad_limpia = _limpiar_texto(localidad)

            if _aparece(localidad_limpia, preg_limpia):
                return provincia, localidad

    return None, None


def _ruido(provincia, localidad) -> set:
    """Palabras que deben excluirse de la búsqueda temática."""
    ruido = set(PALABRAS_GENERICAS)

    for geo in (provincia, localidad):
        if geo:
            ruido.update(_limpiar_texto(geo).split())

    return ruido


def _terminos_tematicos(
    preg_limpia: str,
    provincia,
    localidad,
) -> list:
    """Extrae términos relevantes de una pregunta ya normalizada."""
    ruido = _ruido(provincia, localidad)

    return [
        termino
        for termino in re.findall(r"\w+", preg_limpia)
        if len(termino) > 2 and termino not in ruido
    ]


def _terminos_busqueda(
    pregunta: str,
    provincia,
    localidad,
) -> list:
    """Extrae términos de búsqueda de la pregunta original."""
    ruido = _ruido(provincia, localidad)

    return [
        termino
        for termino in re.findall(r"\w+", pregunta.lower())
        if len(termino) > 2
        and _limpiar_texto(termino) not in ruido
    ]


def _aplicar_filtros_geograficos(
    queryset,
    provincia,
    localidad,
):
    """Aplica los filtros geográficos sin excluir cursos de ámbito general."""
    condicion_general = (
        Q(provincia__iexact="General")
        | Q(provincia__iexact="N/D")
        | Q(provincia__exact="")
        | Q(provincia__isnull=True)
    )

    if provincia:
        localidades_provincia = MAPA_LOCALIDADES_CYL.get(
            provincia,
            [],
        )

        return queryset.filter(
            Q(provincia__icontains=provincia)
            | Q(localidad__in=localidades_provincia)
            | condicion_general
        )

    if localidad:
        return queryset.filter(
            Q(localidad__iexact=localidad)
            | condicion_general
        )

    return queryset


def _primeros_cursos_aprovechables(
    cursos,
    limite=MAX_LISTADO,
):
    """
    Devuelve cursos que contienen información formativa útil.

    Continúa recorriendo los candidatos hasta completar el límite.
    No modifica ni elimina registros de la base de datos.
    """
    resultados = []

    for curso in cursos:
        try:
            aprovechable = _curso_aprovechable(curso)
        except Exception:
            logger.exception(
                "[Retriever] Error evaluando la calidad de la ficha pk=%s",
                getattr(curso, "pk", None),
            )
            continue

        if not aprovechable:
            logger.debug(
                "[Retriever] Ficha descartada por falta de información útil: "
                "pk=%s, titulo=%r",
                getattr(curso, "pk", None),
                getattr(curso, "titulo", None),
            )
            continue

        resultados.append(curso)

        if len(resultados) >= limite:
            break

    return resultados


def _buscar_fts(queryset, terminos: list) -> list:
    """
    Ejecuta la búsqueda en tres fases:

    1. Búsqueda FTS estricta mediante AND.
    2. Búsqueda FTS flexible mediante OR.
    3. Respaldo léxico por subcadenas.

    Devuelve la primera fase que encuentre cursos aprovechables.
    """

    def _fts(texto_consulta: str) -> list:
        query = SearchQuery(
            texto_consulta,
            config="spanish",
            search_type="websearch",
        )

        candidatos = (
            queryset.filter(vector_busqueda=query)
            .annotate(
                rank=SearchRank(
                    F("vector_busqueda"),
                    query,
                    normalization=NORMALIZACION_RANK,
                )
            )
            .filter(rank__gte=UMBRAL_MINIMO)
            .order_by("-rank", "localidad")
        )

        return _primeros_cursos_aprovechables(candidatos)

    # Fase 1: AND estricto.
    resultados = _fts(" ".join(terminos))

    if resultados:
        return resultados

    # Fase 2: OR flexible.
    if len(terminos) > 1:
        logger.debug(
            "[Retriever] AND sin resultados aprovechables; "
            "reintentando con OR."
        )

        resultados = _fts(" or ".join(terminos))

        if resultados:
            return resultados

    # Fase 3: respaldo léxico.
    logger.debug(
        "[Retriever] FTS sin resultados aprovechables; "
        "aplicando respaldo léxico."
    )

    q_icontains = Q()

    for termino in terminos:
        raiz = termino[:6] if len(termino) > 6 else termino

        q_icontains |= (
            Q(contenido__icontains=raiz)
            | Q(titulo__icontains=raiz)
        )

    candidatos = queryset.filter(q_icontains).order_by(
        "localidad",
        "titulo",
    )

    return _primeros_cursos_aprovechables(candidatos)


def recuperar_cursos(
    pregunta: str,
    filtros: dict = None,
) -> list:
    """
    Recupera cursos activos aplicando filtros geográficos,
    temáticos y de calidad de la información.
    """
    filtros = dict(filtros or {})
    pregunta = _corregir_errores_comunes(pregunta or "")
    preg_limpia = _limpiar_texto(pregunta)

    # ------------------------------------------------------------------
    # Caso 0: URL completa o slug de curso.
    # ------------------------------------------------------------------
    url_match = re.search(r"https?://[^\s]+", pregunta)

    if url_match:
        url_extraida = url_match.group(0).strip().rstrip("/")

        logger.debug(
            "[Retriever] URL detectada: %s",
            url_extraida,
        )

        curso = BaseConocimiento.objects.filter(
            url_oficial__icontains=url_extraida,
            activo=True,
        ).first()

        if curso and _curso_aprovechable(curso):
            return [curso]

    # Detección de slug.
    if "/" in pregunta or (
        "-" in pregunta and len(pregunta.strip()) > 15
    ):
        slug_candidato = (
            pregunta.strip().split("/")[-1] or pregunta.strip()
        ).rstrip("/")

        if len(slug_candidato) > 5:
            logger.debug(
                "[Retriever] Slug de curso detectado: %s",
                slug_candidato,
            )

            curso_slug = BaseConocimiento.objects.filter(
                url_oficial__icontains=slug_candidato,
                activo=True,
            ).first()

            if curso_slug and _curso_aprovechable(curso_slug):
                return [curso_slug]

    # ------------------------------------------------------------------
    # Caso 1: consulta automática del catálogo.
    # ------------------------------------------------------------------
    if _es_consulta_automatica(preg_limpia):
        logger.debug(
            "[Retriever] Consulta automática detectada."
        )

        queryset = BaseConocimiento.objects.filter(activo=True)

        provincia = filtros.get("provincia")
        localidad = filtros.get("localidad")
        colectivo = filtros.get("colectivo")

        queryset = _aplicar_filtros_geograficos(
            queryset,
            provincia,
            localidad,
        )

        if colectivo:
            queryset = queryset.filter(colectivo=colectivo)

        resultados = _primeros_cursos_aprovechables(
            queryset.order_by("localidad", "titulo"),
            MAX_LISTADO,
        )

        logger.info(
            "[Retriever] Consulta automática | provincia=%s "
            "localidad=%s colectivo=%s resultados=%d",
            provincia,
            localidad,
            colectivo,
            len(resultados),
        )

        return resultados

    # ------------------------------------------------------------------
    # Caso 2: detección geográfica implícita.
    # ------------------------------------------------------------------
    if not filtros.get("provincia"):
        provincia_detectada, localidad_detectada = (
            _detectar_geografia(preg_limpia)
        )

        if provincia_detectada:
            filtros["provincia"] = provincia_detectada

            if localidad_detectada:
                filtros["localidad"] = localidad_detectada

    queryset = BaseConocimiento.objects.filter(activo=True)

    provincia = filtros.get("provincia")
    localidad = filtros.get("localidad")
    colectivo = filtros.get("colectivo")

    queryset = _aplicar_filtros_geograficos(
        queryset,
        provincia,
        localidad,
    )

    if colectivo:
        queryset = queryset.filter(colectivo=colectivo)

    # ------------------------------------------------------------------
    # Caso 3: listado directo por provincia o geografía.
    # ------------------------------------------------------------------
    if provincia and any(
        palabra in preg_limpia
        for palabra in PALABRAS_LISTADO
    ):
        logger.debug(
            "[Retriever] Palabra de listado detectada."
        )

        return _primeros_cursos_aprovechables(
            queryset.order_by("localidad", "titulo"),
            MAX_LISTADO,
        )

    if (
        (provincia or localidad)
        and not _terminos_tematicos(
            preg_limpia,
            provincia,
            localidad,
        )
    ):
        logger.debug(
            "[Retriever] Consulta geográfica pura."
        )

        return _primeros_cursos_aprovechables(
            queryset.order_by("localidad", "titulo"),
            MAX_LISTADO,
        )

    # ------------------------------------------------------------------
    # Caso 4: búsqueda temática.
    # ------------------------------------------------------------------
    terminos = _terminos_busqueda(
        pregunta,
        provincia,
        localidad,
    )

    if not terminos:
        logger.debug(
            "[Retriever] Sin términos temáticos tras la limpieza."
        )
        return []

    resultados = _buscar_fts(queryset, terminos)

    logger.debug(
        "[Retriever] Términos=%s | resultados=%d",
        terminos,
        len(resultados),
    )

    return resultados