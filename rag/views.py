# rag/views.py
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from celery.result import AsyncResult

from .serializers import ChatRequestSerializer
from .tasks import procesar_chat_ia_task

logger = logging.getLogger(__name__)

@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', block=False)
def chat_ask_view(request):
    """
    Endpoint asíncrono: Valida la entrada y deriva la inferencia de IA a Celery,
    liberando instantáneamente el worker de Gunicorn.
    """
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Demasiadas solicitudes. Has superado el límite de 5 peticiones por minuto."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    # 1. Validación estricta con DRF
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True) 
    
    pregunta = serializer.validated_data['pregunta']
    filtros = serializer.validated_data.get('filtros', {})
    sesion_uuid = request.data.get('sesion_uuid')

    # 2. Despacho inmediato a la cola de Redis (Cero bloqueo HTTP)
    task = procesar_chat_ia_task.delay(pregunta, filtros, sesion_uuid)

    return Response({
        "mensaje": "Consulta en proceso",
        "task_id": task.id
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def chat_status_view(request, task_id):
    """
    Endpoint de polling para que el cliente consulte el estado de la inferencia en Redis.
    """
    tarea = AsyncResult(task_id)
    
    respuesta = {
        "task_id": task_id,
        "estado": tarea.status  # PENDING, STARTED, SUCCESS, FAILURE
    }
    
    if tarea.status == 'SUCCESS':
        respuesta["resultado"] = tarea.result
    elif tarea.status == 'FAILURE':
        respuesta["error"] = "Error interno ejecutando la inferencia de la IA o timeout en el worker."
        
    return Response(respuesta, status=status.HTTP_200_OK)