# rag/views.py
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit

from .serializers import ChatRequestSerializer
from .retriever import recuperar_cursos
from .generator import generar_respuesta_ia
from .models import ConsultaFallida

logger = logging.getLogger(__name__)

@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', block=False)
def chat_ask_view(request):
    """
    Endpoint síncrono: Valida la entrada, ejecuta la recuperación RAG y la inferencia con la IA,
    devolviendo la respuesta directamente para el widget de cefye.com.
    """
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Demasiadas solicitudes. Has superado el límite de 5 peticiones por minuto."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    # 1. Validación estricta con DRF (mantiene la validación del esquema)
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True) 
    
    pregunta = serializer.validated_data['pregunta']
    filtros = serializer.validated_data.get('filtros', {})

    try:
        # 2. Ejecución síncrona del pipeline RAG y LLM
        resultados = recuperar_cursos(pregunta, filtros)
        respuesta_ia = generar_respuesta_ia(pregunta, resultados)

        return Response({
            "texto_respuesta": respuesta_ia.get("texto_respuesta"),
            "fuentes": [str(r) for r in resultados]
        }, status=status.HTTP_200_OK)

    except Exception as exc:
        logger.error(f"Error procesando chatbot: {exc}")
        
        # Registramos el fallo en la base de datos para la telemetría
        try:
            ConsultaFallida.objects.create(texto_consulta=pregunta, motivo_fallo=str(exc))
        except Exception as db_exc:
            logger.error(f"No se pudo registrar el fallo en telemetría: {db_exc}")

        return Response(
            {"error": "Error interno al procesar la consulta con la IA."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )