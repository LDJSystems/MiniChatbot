import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APIClient
from telemetry.models import ConsultaFallida, ContadorDemanda
from django.db import DatabaseError
from rag.tasks import procesar_chat_ia_task
from django.core.cache import cache
from django.test import override_settings

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
@override_settings(
    RATELIMIT_ENABLE=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
@patch('rag.views.procesar_chat_ia_task.delay')
def test_ratelimit_aislado_por_ip(mock_task_delay, api_client):
    mock_task_delay.return_value.id = "123e4567-e89b-12d3-a456-426614174000"
    cache.clear()
    url = reverse('api_rag_ask')
    
    for _ in range(5):
        response = api_client.post(
            url, 
            {'pregunta': 'Test'}, 
            format='json', 
            REMOTE_ADDR='192.168.1.50'
        )
        assert response.status_code != 429

    response = api_client.post(
        url, 
        {'pregunta': 'Test'}, 
        format='json', 
        REMOTE_ADDR='192.168.1.50'
    )
    assert response.status_code == 429

    response = api_client.post(
        url, 
        {'pregunta': 'Test'}, 
        format='json', 
        REMOTE_ADDR='10.0.0.99'
    )
    assert response.status_code != 429

@pytest.mark.django_db
@patch('rag.views.procesar_chat_ia_task.delay')
def test_chat_ask_retorna_202_y_encola(mock_task_delay, api_client):
    # Forzar un ID explícito simulado en lugar de dejar que el mock devuelva otro mock
    mock_task_delay.return_value.id = "123e4567-e89b-12d3-a456-426614174000"

    url = reverse('api_rag_ask')
    response = api_client.post(url, {'pregunta': '¿Hay cursos en León?'}, format='json')
    
    assert response.status_code == 202
    assert response.data["task_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert response.data["mensaje"] == "Consulta en proceso"
    mock_task_delay.assert_called_once()

@pytest.mark.django_db
def test_chat_ask_payload_invalido_retorna_400(api_client):
    url = reverse('api_rag_ask')
    # Payload incompleto (falta el campo obligatorio 'pregunta')
    response = api_client.post(url, {}, format='json')
    
    assert response.status_code == 400

@pytest.mark.django_db
@patch('rag.tasks.generar_respuesta_ia')
@patch('rag.tasks.recuperar_cursos')
def test_task_fallo_llm_registra_telemetria(mock_recuperar, mock_generar):
    class DummyResult:
        id = 1
        provincia = 'León'
        
    mock_recuperar.return_value = [DummyResult()]
    mock_generar.side_effect = Exception("Timeout de Ollama")
    
    with pytest.raises(Exception):
        procesar_chat_ia_task.delay(
            pregunta='¿Hay cursos en León?', 
            filtros={}, 
            sesion_uuid=None
        )
        
    fallo = ConsultaFallida.objects.first()
    assert fallo is not None
    assert fallo.texto_consulta == '¿Hay cursos en León?'
    assert fallo.motivo_fallo == 'error_llm'
    
@pytest.mark.django_db
@patch('rag.tasks.generar_respuesta_ia')
@patch('rag.tasks.recuperar_cursos')
def test_task_fallo_llm_registra_telemetria(mock_recuperar, mock_generar):
    class DummyResult:
        id = 1
        provincia = 'León'

    mock_recuperar.return_value = [DummyResult()]
    mock_generar.side_effect = Exception("Timeout de Ollama")

    with pytest.raises(Exception, match="Timeout de Ollama"):
        procesar_chat_ia_task.apply(
            args=('¿Hay cursos en León?', {}, None),
            throw=True,
        )

    fallo = ConsultaFallida.objects.first()

    assert fallo is not None
    assert fallo.texto_consulta == '¿Hay cursos en León?'
    assert fallo.motivo_fallo == 'error_llm'

@pytest.mark.django_db
@patch('rag.tasks.generar_respuesta_ia')
@patch('rag.tasks.recuperar_cursos')
def test_task_exito_incremento_atomico(mock_recuperar, mock_generar):
    class DummyResult:
        id = 1
        provincia = 'León'
        
    mock_recuperar.return_value = [DummyResult()]
    mock_generar.return_value = {"texto_respuesta": "Sí, hay cursos"}
    
    ContadorDemanda.objects.create(base_conocimiento_id=1, demanda=5)
    
    procesar_chat_ia_task.apply(args=('Cursos de Python', {}, None))
    
    contador = ContadorDemanda.objects.get(base_conocimiento_id=1)
    assert contador.demanda == 6