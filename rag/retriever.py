# rag/retriever.py
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

UMBRAL_MINIMO = 0.12

def recuperar_cursos(pregunta: str, filtros: dict = None) -> list:
    query = SearchQuery(pregunta, config='spanish')
    
    queryset = BaseConocimiento.objects.filter(activo=True)
    if filtros:
        if provincia := filtros.get('provincia'):
            queryset = queryset.filter(provincia=provincia)
        if campo := filtros.get('campo_estudio'):
            queryset = queryset.filter(campo_estudio=campo)
        if colectivo := filtros.get('colectivo'):
            queryset = queryset.filter(colectivo=colectivo)

    resultados = queryset.filter(
        vector_busqueda=query
    ).annotate(
        rank=SearchRank('vector_busqueda', query)
    ).filter(
        rank__gte=UMBRAL_MINIMO
    ).order_by('-rank')[:3]

    return list(resultados)