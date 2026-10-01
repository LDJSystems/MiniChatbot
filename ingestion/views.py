from django.http import JsonResponse
from ingestion.scraper import extraer_cursos_cefye  # O la función que utilices

def debug_scraper_view(request):
    """Ejecuta el scraper al vuelo y devuelve los datos brutos extraídos del frontend."""
    try:
        datos_extraidos = extraer_cursos_cefye()  # Función que realiza el parseo de cefye.com
        return JsonResponse({
            "status": "success",
            "total_elementos": len(datos_extraidos),
            "elementos": datos_extraidos
        }, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({"status": "error", "detalles": str(e)}, status=500)