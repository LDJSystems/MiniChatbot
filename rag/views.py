# rag/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
import json

from rag.validators import validar_chat_request
from rag.retriever import recuperar_cursos
from rag.generator import generar_respuesta_ia

@ratelimit(key='ip', rate='5/m', block=False)
@require_POST
def chat_ask_view(request):
    if getattr(request, 'limited', False):
        return JsonResponse({"error": "Demasiadas peticiones. Límite excedido."}, status=429)

    try:
        body = json.loads(request.body)
        pregunta, filtros = validar_chat_request(body)
        
        resultados = recuperar_cursos(pregunta, filtros)
        resultado_ia = generar_respuesta_ia(pregunta, resultados)
        
        return JsonResponse({
            "texto_respuesta": resultado_ia["texto_respuesta"],
            "requiere_accion_comercial": resultado_ia["requiere_accion_comercial"],
            "fallback_activado": resultado_ia["fallback_activado"]
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)