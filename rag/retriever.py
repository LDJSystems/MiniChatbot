import re
import logging
from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

logger = logging.getLogger(__name__)

# Umbral mínimo de rank. El filtro `vector_busqueda=query` ya garantiza que el curso
# contiene los términos, así que el umbral solo descarta coincidencias muy débiles.
# Con el rank calculado sobre vector_busqueda (peso 'A') y normalization=1,
# una coincidencia simple ronda 0.07-0.15, por eso el umbral es bajo.
UMBRAL_MINIMO = 0.01

# 0 = sin normalizar | 1 = divide por 1 + log(longitud) | 2 = divide por la longitud.
# Con 2 los textos largos quedan muy por debajo de cualquier umbral razonable.
NORMALIZACION_RANK = 1

MAX_LISTADO = 15

MAPA_LOCALIDADES_CYL = {
    "Ávila": ["Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda", "El Barco de Ávila", "Las Navas del Marqués"],
    "Burgos": ["Burgos", "Miranda de Ebro", "Aranda de Duero", "Briviesca", "Medina de Pomar", "Villarcayo de Merindad de Castilla La Vieja"],
    "León": ["León", "Leon", "León Capital", "Leon Capital", "León ciudad", "Ponferrada", "San Andrés del Rabanedo", "Villaquilambre", "Astorga", "La Bañeza", "Bembibre", "Valencia de Don Juan"],
    "Palencia": ["Palencia", "Aguilar de Campoo", "Guardo", "Venta de Baños", "Villamuriel de Cerrato", "Herrera de Pisuerga"],
    "Salamanca": ["Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes", "Carbajosa de la Sagrada", "Peñaranda de Bracamonte", "Guijuelo"],
    "Segovia": ["Segovia", "Cuéllar", "El Espinar", "Real Sitio de San Ildefonso", "Palazuelos de Eresma", "Nava de la Asunción"],
    "Soria": ["Soria", "Almazán", "El Burgo de Osma-Ciudad de Osma", "Golmayo", "San Esteban de Gormaz", "Ágreda"],
    "Valladolid": ["Valladolid", "Laguna de Duero", "Medina del Campo", "Arroyo de la Encomienda", "Tordesillas", "Cistérniga", "Zaratán", "Simancas"],
    "Zamora": ["Zamora", "Benavente", "Toro", "Morales del Vino", "Puebla de Sanabria", "Villaralbo"],
}

TRANSLATION_TABLE = str.maketrans('áéíóúñ', 'aeioun')

# Palabras que no aportan tema a la búsqueda (sin acentos, en minúsculas)
PALABRAS_GENERICAS = {
    "formacion", "curso", "cursos", "en", "de", "del", "la", "el", "los", "las",
    "para", "por", "con", "sobre", "quiero", "busco", "hay", "tengo", "necesito",
    "dame", "un", "una", "y", "o", "que", "tienen", "teneis", "como", "donde",
    "cefye", "gratuita", "gratuito", "gratis",
}

PALABRAS_LISTADO = ("todos", "listar", "muestrame", "provincia", "listado")


def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    return texto.lower().translate(TRANSLATION_TABLE)


def _aparece(frase_limpia: str, texto_limpio: str) -> bool:
    """True si la frase aparece como palabra(s) completa(s), no como subcadena.
    Evita falsos positivos como 'toro' dentro de 'motor' o 'soria' dentro de otra palabra."""
    return re.search(rf'\b{re.escape(frase_limpia)}\b', texto_limpio) is not None


def _detectar_geografia(preg_limpia: str):
    """Devuelve (provincia, localidad) detectadas en la pregunta; None si no hay."""
    for prov, localidades in MAPA_LOCALIDADES_CYL.items():
        if _aparece(_limpiar_texto(prov), preg_limpia):
            return prov, None
        for loc in localidades:
            if _aparece(_limpiar_texto(loc), preg_limpia):
                return prov, loc
    return None, None


def _ruido(provincia, localidad) -> set:
    ruido = set(PALABRAS_GENERICAS)
    for geo in (provincia, localidad):
        if geo:
            ruido.update(_limpiar_texto(geo).split())
    return ruido


def _terminos_tematicos(preg_limpia: str, provincia, localidad) -> list:
    """Términos de la consulta que no son genéricos ni geográficos (versión sin tildes)."""
    ruido = _ruido(provincia, localidad)
    return [t for t in re.findall(r'\w+', preg_limpia) if len(t) > 2 and t not in ruido]


def _terminos_busqueda(pregunta: str, provincia, localidad) -> list:
    """Términos temáticos CON sus tildes originales, listos para el full-text.

    El diccionario 'spanish' de Postgres no quita tildes: 'programación' hace
    stemming a 'program' y casa con el contenido, mientras que 'programacion'
    (sin tilde) no. Por eso la comparación con el ruido se hace en versión
    limpia, pero el término que se envía es el original.
    """
    ruido = _ruido(provincia, localidad)
    return [
        t for t in re.findall(r'\w+', pregunta.lower())
        if len(t) > 2 and _limpiar_texto(t) not in ruido
    ]


def recuperar_cursos(pregunta: str, filtros: dict = None) -> list:
    # Copia para no mutar el dict del llamador
    filtros = dict(filtros or {})

    preg_limpia = _limpiar_texto(pregunta)

    # Detección geográfica si no viene forzada en los filtros
    if not filtros.get('provincia'):
        prov_detectada, loc_detectada = _detectar_geografia(preg_limpia)
        if prov_detectada:
            filtros['provincia'] = prov_detectada
            if loc_detectada:
                filtros['localidad'] = loc_detectada

    queryset = BaseConocimiento.objects.filter(activo=True)

    provincia = filtros.get('provincia')
    localidad = filtros.get('localidad')
    campo = filtros.get('campo_estudio')
    colectivo = filtros.get('colectivo')

    # Filtros geográficos inclusivos (evita que desaparezcan cursos generales)
    condicion_general = (
        Q(provincia__iexact='General') |
        Q(provincia__iexact='N/D') |
        Q(provincia__exact='') |
        Q(provincia__isnull=True)
    )

    if provincia:
        localidades_provincia = MAPA_LOCALIDADES_CYL.get(provincia, [])
        queryset = queryset.filter(
            Q(provincia__icontains=provincia) |
            Q(localidad__in=localidades_provincia) |
            condicion_general
        )
    elif localidad:
        queryset = queryset.filter(
            Q(localidad__iexact=localidad) |
            condicion_general
        )

    if campo:
        queryset = queryset.filter(campo_estudio=campo)
    if colectivo:
        queryset = queryset.filter(colectivo=colectivo)

    # Cortocircuito para consultas explícitas de listados
    if provincia and any(k in preg_limpia for k in PALABRAS_LISTADO):
        return list(queryset.order_by('localidad', 'titulo')[:MAX_LISTADO])

    # Consulta puramente geográfica ("formación en León"): sin tema que buscar,
    # se devuelve el listado de la zona en vez de exigir coincidencia full-text.
    if (provincia or localidad) and not _terminos_tematicos(preg_limpia, provincia, localidad):
        return list(queryset.order_by('localidad', 'titulo')[:MAX_LISTADO])

    # Búsqueda full-text solo con términos temáticos (la geografía ya filtró arriba)
    terminos = _terminos_busqueda(pregunta, provincia, localidad)
    if not terminos:
        logger.debug("[Retriever] Sin términos temáticos tras limpiar la pregunta.")
        return []

    def _buscar(texto_consulta: str) -> list:
        query = SearchQuery(texto_consulta, config='spanish', search_type='websearch')
        # El filtro usa el índice GIN de vector_busqueda. El rank se calcula sobre el
        # mismo vector, que ya se construye solo con 'contenido' (migración 0008),
        # así que no hace falta recalcular to_tsvector en cada fila.
        return list(
            queryset.filter(vector_busqueda=query)
            .annotate(
                rank=SearchRank(
                    F('vector_busqueda'),
                    query,
                    normalization=NORMALIZACION_RANK,
                )
            )
            .filter(rank__gte=UMBRAL_MINIMO)
            .order_by('-rank', 'localidad')
        )

    # 1º todos los términos (AND); 2º si no hay nada, cualquiera de ellos (OR)
    resultados = _buscar(" ".join(terminos))
    if not resultados and len(terminos) > 1:
        resultados = _buscar(" or ".join(terminos))

    logger.debug(f"[Retriever] Términos={terminos} | resultados={len(resultados)}")
    return resultados