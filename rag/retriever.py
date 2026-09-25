from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

class HybridRetriever:
    UMBRAL_MINIMO = 0.12

    @staticmethod
    def recuperar(pregunta: str, filtros: dict = None) -> list:
        query = SearchQuery(pregunta, config='spanish')
        
        # Fase 1: Pre-filtro categórico opcional
        queryset = BaseConocimiento.objects.filter(activo=True)
        if filtros:
            if provincia := filtros.get('provincia'):
                queryset = queryset.filter(provincia=provincia)
            if campo := filtros.get('campo_estudio'):
                queryset = queryset.filter(campo_estudio=campo)
            if colectivo := filtros.get('colectivo'):
                queryset = queryset.filter(colectivo=colectivo)

        # Fase 2: FTS, anotación de ranking y corte estricto
        resultados = queryset.filter(
            vector_busqueda=query
        ).annotate(
            rank=SearchRank('vector_busqueda', query)
        ).filter(
            rank__gte=HybridRetriever.UMBRAL_MINIMO
        ).order_by('-rank')[:3]

        return list(resultados)