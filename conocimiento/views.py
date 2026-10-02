from django.http import JsonResponse
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.views.decorators.http import require_POST
import json
from conocimiento.models import BaseConocimiento
from conocimiento.services import ChatbotKnowledgeService

def buscar_conocimiento_view(request):
    query_str = request.GET.get('q', '').strip()
    if not query_str:
        return JsonResponse({'resultados': []}, status=200)
    
    query = SearchQuery(query_str, config='spanish')
    
    # Consulta optimizada usando vector_busqueda y ordenando por relevancia (rank)[cite: 3]
    resultados = BaseConocimiento.objects.filter(
        vector_busqueda=query,
        activo=True
    ).annotate(
        rank=SearchRank('vector_busqueda', query)
    ).order_by('-rank')[:5]

    data = [
        {
            'titulo': r.titulo,
            'contenido': r.contenido,
            'provincia': r.provincia,
            'campo_estudio': r.campo_estudio,
            'colectivo': r.colectivo,
            'url_oficial': r.url_oficial,
            'relevancia': r.rank
        }
        for r in resultados
    ]
    
    return JsonResponse({'resultados': data}, status=200)