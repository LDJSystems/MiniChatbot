import logging
from django.db import models
from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

logger = logging.getLogger(__name__)

# 1. Umbral calibrado (Fase 4)
UMBRAL_MINIMO = 0.12

MAPA_LOCALIDADES_CYL = {
    "Ávila": ["Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda", "El Barco de Ávila", "Las Navas del Marqués"],
    "Burgos": ["Burgos", "Miranda de Ebro", "Aranda de Duero", "Briviesca", "Medina de Pomar", "Villarcayo de Merindad de Castilla La Vieja"],
    "León": ["León", "Leon", "León Capital", "Leon Capital", "León ciudad", "Ponferrada", "San Andrés del Rabanedo", "Villaquilambre", "Astorga", "La Bañeza", "Bembibre", "Valencia de Don Juan"],
    "Palencia": ["Palencia", "Aguilar de Campoo", "Guardo", "Venta de Baños", "Villamuriel de Cerrato", "Herrera de Pisuerga"],
    "Salamanca": ["Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes", "Carbajosa de la Sagrada", "Peñaranda de Bracamonte", "Guijuelo"],
    "Segovia": ["Segovia", "Cuéllar", "El Espinar", "Real Sitio de San Ildefonso", "Palazuelos de Eresma", "Nava de la Asunción"],
    "Soria": ["Soria", "Almazán", "El Burgo de Osma-Ciudad de Osma", "Golmayo", "San Esteban de Gormaz", "Ágreda"],
    "Valladolid": ["Valladolid", "Laguna de Duero", "Medina del Campo", "Arroyo de la Encomienda", "Tordesillas", "Cistérniga", "Zaratán", "Simancas"],
    "Zamora": ["Zamora", "Benavente", "Toro", "Morales del Vino", "Puebla de Sanabria", "Villaralbo"]
}

TRANSLATION_TABLE = str.maketrans('áéíóúñ', 'aeioun')

def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    return texto.lower().translate(TRANSLATION_TABLE)

def recuperar_cursos(pregunta: str, filtros: dict = None) -> list:
    if filtros is None:
        filtros = {}
        
    preg_limpia = _limpiar_texto(pregunta)

    # Detección geográfica si no viene forzada en los filtros
    if not filtros.get('provincia'):
        encontrado = False
        for prov, localidades in MAPA_LOCALIDADES_CYL.items():
            if _limpiar_texto(prov) in preg_limpia:
                filtros['provincia'] = prov
                encontrado = True
            else:
                for loc in localidades:
                    if _limpiar_texto(loc) in preg_limpia:
                        filtros['provincia'] = prov
                        filtros['localidad'] = loc
                        encontrado = True
                        break
            if encontrado:
                break

    queryset = BaseConocimiento.objects.filter(activo=True)
    
    provincia = filtros.get('provincia')
    localidad = filtros.get('localidad')
    campo = filtros.get('campo_estudio')
    colectivo = filtros.get('colectivo')

    # 2. Filtros Geográficos Inclusivos (Evitar que desaparezcan cursos generales)
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
    elif localidad: # Si hay localidad pero por algún motivo no provincia
        queryset = queryset.filter(
            Q(localidad__iexact=localidad) |
            condicion_general
        )

    if campo:
        queryset = queryset.filter(campo_estudio=campo)
    if colectivo:
        queryset = queryset.filter(colectivo=colectivo)

    # Cortocircuito para consultas explícitas de listados
    palabras_listado = ["todos", "listar", "muestrame", "provincia", "listado"]
    if any(k in preg_limpia for k in palabras_listado) and provincia:
        return list(queryset.order_by('localidad', 'titulo')[:15])

    # 3. Búsqueda Full-Text optimizada con Websearch
    # 'websearch' descarta palabras de ruido (el, la, un) automáticamente y entiende lenguaje natural
    query = SearchQuery(pregunta, config='spanish', search_type='websearch')
    
    resultados = list(
        queryset.filter(
            vector_busqueda=query
        ).annotate(
            # normalization=2 divide el rank por el logaritmo de la longitud del documento
            # Esto evita que los cursos con descripciones gigantes salgan siempre primeros
            rank=SearchRank(F('vector_busqueda'), query, normalization=2)
        ).filter(
            rank__gte=UMBRAL_MINIMO
        ).order_by('-rank', 'localidad')
    )

    logger.debug(f"[Retriever] Total resultados devueltos: {len(resultados)}")
    return resultados