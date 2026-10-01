import re
import logging
import operator
from functools import reduce
from django.db import models
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

logger = logging.getLogger(__name__)

UMBRAL_MINIMO = 0.01

STOPWORDS = {
    "que", "con", "los", "las", "del", "para", "una", "uno", "como",
    "por", "sus", "hay", "son", "mas", "pero", "esta", "este", "hay",
    "donde", "cuando", "cual", "cuales", "quien", "quienes", "sobre",
    "entre", "desde", "hasta", "sin", "tras", "ante", "bajo", "segun"
}

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

# Tabla de traducción compilada una sola vez a nivel de módulo
TRANSLATION_TABLE = str.maketrans('áéíóúñ', 'aeioun')

def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    return texto.lower().translate(TRANSLATION_TABLE)

def recuperar_cursos(pregunta: str, filtros: dict = None) -> list:
    if filtros is None:
        filtros = {}
        
    preg_limpia = _limpiar_texto(pregunta)
    tokens_geograficos = set()

    if not filtros.get('provincia'):
        encontrado = False
        for prov, localidades in MAPA_LOCALIDADES_CYL.items():
            tokens_geograficos.add(_limpiar_texto(prov))
            for loc in localidades:
                for w in _limpiar_texto(loc).split():
                    tokens_geograficos.add(w)
            
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

    palabras_listado = ["todos", "listar", "muestrame", "provincia", "listado"]
    es_consulta_amplia = any(k in preg_limpia for k in palabras_listado)

    queryset = BaseConocimiento.objects.filter(activo=True)
    
    provincia = filtros.get('provincia')
    localidad = filtros.get('localidad')
    campo = filtros.get('campo_estudio')
    colectivo = filtros.get('colectivo')

    if provincia:
        localidades_provincia = MAPA_LOCALIDADES_CYL.get(provincia, [])
        queryset = queryset.filter(
            models.Q(provincia__icontains=provincia) | 
            models.Q(localidad__in=localidades_provincia)
        )
    if localidad:
        queryset = queryset.filter(localidad__iexact=localidad)
    if campo:
        queryset = queryset.filter(campo_estudio=campo)
    if colectivo:
        queryset = queryset.filter(colectivo=colectivo)

    if es_consulta_amplia and provincia:
        resultados = list(queryset.order_by('localidad', 'titulo')[:10])
    else:
        terminos = [
            w for w in re.findall(r'\w+', pregunta)
            if len(w) > 2
            and _limpiar_texto(w) not in tokens_geograficos
            and _limpiar_texto(w) not in STOPWORDS
        ]

        if not terminos:
            terminos = ["curso", "formacion", "taller", "empleo"]

        logger.debug(f"[Retriever] Términos de búsqueda finales: {terminos}")

        query = reduce(operator.or_, [SearchQuery(t, config='spanish') for t in terminos])
        resultados = list(
            queryset.filter(
                vector_busqueda=query
            ).annotate(
                rank=SearchRank('vector_busqueda', query)
            ).filter(
                rank__gte=UMBRAL_MINIMO
            ).order_by('localidad', '-rank')
        )

        logger.debug(f"[Retriever] Resultados full-text: {len(resultados)}")

        # Fallback geográfico estricto: localidad__iexact para evitar falsos positivos
        if not resultados:
            if localidad:
                logger.debug(f"[Retriever] Fallback geográfico activado para localidad: {localidad}")
                resultados = list(
                    queryset.filter(localidad__iexact=localidad)
                    .order_by('titulo')
                )
            elif provincia:
                logger.debug(f"[Retriever] Fallback geográfico activado para provincia: {provincia}")
                resultados = list(queryset.order_by('localidad', 'titulo'))

    logger.debug(f"[Retriever] Total resultados devueltos: {len(resultados)}")
    return resultados