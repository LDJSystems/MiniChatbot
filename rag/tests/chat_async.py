import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch

@pytest.fixture(autouse=True)
def celery_eager(settings):
    """
    Cortocircuito de infraestructura para TDD:
    Ejecuta las tareas de Celery en el mismo hilo sin requerir Redis activo.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

@pytest.mark.django_db
@patch('rag.retriever.recuperar_cursos')
@patch('rag.generator.generar_respuesta_ia')
def test_chat_ask_delega_a_celery_y_retorna_202(mock_generar, mock_recuperar, client):
    # Mockeamos el I/O pesado (Ollama/DB) para testear estrictamente la capa de red
    mock_recuperar.return_value = []
    mock_generar.return_value = {"texto_respuesta": "Respuesta mock"}

    url_ask = reverse('chat-ask')  # Ajusta si tu url name es diferente
    payload = {"pregunta": "¿Qué cursos de programación hay en Leon?"}
    
    response = client.post(url_ask, data=payload, content_type="application/json")
    
    assert response.status_code == status.HTTP_202_ACCEPTED, f"Se esperaba 202, se obtuvo {response.status_code}"
    
    data = response.json()
    assert "task_id" in data, "La respuesta HTTP 202 no incluye el task_id para el polling."
    assert data["mensaje"] == "Consulta en proceso"

@pytest.mark.django_db
def test_chat_status_endpoint_devuelve_formato_correcto(client):
    # Generamos un UUID falso para probar la estructura del endpoint de polling
    task_id_falso = "123e4567-e89b-12d3-a456-426614174000"
    url_status = reverse('chat-status', kwargs={'task_id': task_id_falso})
    
    response = client.get(url_status)
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "estado" in data, "El endpoint de status no declara el estado de la tarea."
    assert data["estado"] in ["PENDING", "SUCCESS", "FAILURE"]