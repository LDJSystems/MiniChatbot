from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
import json

from rag.serializers import ChatRequestValidator
from rag.retriever import HybridRetriever
from rag.generator import HybridGenerator

@ratelimit(key='ip', rate='5/m', block=False)
@require_POST
def chat_ask_view(request):
    if getattr(request, 'limited', False):
        return JsonResponse({"error": "Demasiadas peticiones. Límite excedido."}, status=429)

    try:
        body = json.loads(request.body)
        pregunta, filtros = ChatRequestValidator.validar(body)
        
        resultados = HybridRetriever.recuperar(pregunta, filtros)
        resultado_ia = HybridGenerator.generar_respuesta(pregunta, resultados)
        
        payload_respuesta = {
            "texto_respuesta": resultado_ia["texto_respuesta"],
            "requiere_accion_comercial": resultado_ia["requiere_accion_comercial"],
            "fallback_activado": resultado_ia["fallback_activado"]
        }
        
        return JsonResponse(payload_respuesta, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)