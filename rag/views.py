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
    Endpoint síncrono: valida la entrada, ejecuta el pipeline RAG y devuelve
    la respuesta con los flags que el widget necesita para decidir su siguiente estado.

    Contrato de respuesta (siempre los tres campos):
        texto_respuesta          str   — texto generado por Ollama o mensaje de fallback
        fallback_activado        bool  — True si el retriever no encontró resultados
        requiere_accion_comercial bool — True si el LLM sugiere contacto humano o está caído
    """
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Demasiadas solicitudes. Has superado el límite de 5 peticiones por minuto."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # 1. Validación de entrada
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    pregunta = serializer.validated_data['pregunta']
    filtros  = serializer.validated_data['filtros']

    try:
        # 2. Recuperación RAG
        resultados = recuperar_cursos(pregunta, filtros)

        # 3. Si el retriever no encontró nada, fallback directo sin llamar al LLM
        if not resultados:
            logger.info(f"[RAG] Sin resultados para: '{pregunta}' | filtros={filtros}")

            try:
                ConsultaFallida.objects.create(
                    texto_consulta=pregunta,
                    motivo_fallo="Sin resultados en el retriever",
                )
            except Exception as db_exc:
                logger.error(f"[RAG] No se pudo registrar ConsultaFallida: {db_exc}")

            return Response({
                "texto_respuesta": (
                    "No he encontrado formación que coincida con tu consulta. "
                    "¿Quieres que un asesor de nuestro equipo se ponga en contacto contigo?"
                ),
                "fallback_activado": True,
                "requiere_accion_comercial": True,
            }, status=status.HTTP_200_OK)

        # 4. Generación con Ollama — el generator ya incluye los tres flags
        respuesta_ia = generar_respuesta_ia(pregunta, resultados)

        return Response({
            "texto_respuesta":           respuesta_ia.get("texto_respuesta", ""),
            "fallback_activado":         respuesta_ia.get("fallback_activado", False),
            "requiere_accion_comercial": respuesta_ia.get("requiere_accion_comercial", False),
        }, status=status.HTTP_200_OK)

    except Exception as exc:
        logger.error(f"[RAG] Error inesperado procesando '{pregunta}': {exc}")

        try:
            ConsultaFallida.objects.create(
                texto_consulta=pregunta,
                motivo_fallo=str(exc),
            )
        except Exception as db_exc:
            logger.error(f"[RAG] No se pudo registrar ConsultaFallida: {db_exc}")

        return Response(
            {"error": "Error interno al procesar la consulta con la IA."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )