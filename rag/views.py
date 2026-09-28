from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
import json

from rag.validators import validar_chat_request
from rag.retriever import recuperar_cursos
from rag.generator import generar_respuesta_ia
from operaciones.models import ConsultaFallida, ContadorDemanda

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

        # Registro de telemetría según el resultado del RAG
        if resultado_ia["fallback_activado"]:
            ConsultaFallida.objects.create(
                consulta=pregunta,
                provincia=filtros.get("provincia"),
                campo_estudio=filtros.get("campo_estudio"),
                colectivo=filtros.get("colectivo")
            )
        else:
            for curso in resultados:
                contador, _ = ContadorDemanda.objects.get_or_create(curso=curso)
                contador.demanda += 1
                contador.save()
        
        return JsonResponse({
            "texto_respuesta": resultado_ia["texto_respuesta"],
            "requiere_accion_comercial": resultado_ia["requiere_accion_comercial"],
            "fallback_activado": resultado_ia["fallback_activado"]
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)