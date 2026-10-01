import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APIClient
from telemetry.models import ConsultaFallida, ContadorDemanda
from django.db import DatabaseError

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
@patch('rag.views.generar_respuesta_ia')
@patch('rag.views.recuperar_cursos')
def test_ask_fallo_llm_registra_telemetria(mock_recuperar, mock_generar, api_client):
    # Usamos objetos compatibles con la lógica aunque estén mockeados
    class DummyResult:
        id = 1
        provincia = 'León'
        titulo = 'Test'
        contenido = 'Test'
        url_oficial = 'Test'
        
    mock_recuperar.return_value = [DummyResult()]
    mock_generar.side_effect = Exception("Timeout de Ollama")
    
    url = reverse('api_rag_ask')
    response = api_client.post(url, {'pregunta': '¿Hay cursos en León?'}, format='json')
    
    assert response.status_code == 503
    fallo = ConsultaFallida.objects.first()
    assert fallo is not None
    assert fallo.texto_consulta == '¿Hay cursos en León?'
    assert fallo.motivo_fallo == 'error_llm'

@pytest.mark.django_db
@patch('rag.views.generar_respuesta_ia')
@patch('rag.views.recuperar_cursos', return_value=[])
def test_ask_sin_resultados_registra_telemetria(mock_recuperar, mock_generar, api_client):
    mock_generar.return_value = {"texto_respuesta": "No tengo información", "fallback_activado": True}
    
    url = reverse('api_rag_ask')
    response = api_client.post(url, {'pregunta': 'Curso de cría de dragones'}, format='json')
    
    assert response.status_code == 200
    assert ConsultaFallida.objects.filter(motivo_fallo='sin_resultados').exists()

@pytest.mark.django_db
@patch('rag.views.generar_respuesta_ia')
@patch('rag.views.recuperar_cursos')
def test_ask_exito_incremento_atomico(mock_recuperar, mock_generar, api_client):
    class DummyResult:
        id = 1
        provincia = 'León'
        titulo = 'Test'
        contenido = 'Test'
        url_oficial = 'Test'
        
    mock_recuperar.return_value = [DummyResult()]
    mock_generar.return_value = {"texto_respuesta": "Sí, hay cursos", "fallback_activado": False}
    
    ContadorDemanda.objects.create(base_conocimiento_id=1, demanda=5)
    
    url = reverse('api_rag_ask')
    response = api_client.post(url, {'pregunta': 'Cursos de Python'}, format='json')
    
    assert response.status_code == 200
    contador = ContadorDemanda.objects.get(base_conocimiento_id=1)
    assert contador.demanda == 6

@pytest.mark.django_db
@patch('telemetry.models.ContadorDemanda.objects.filter')
@patch('rag.views.generar_respuesta_ia')
@patch('rag.views.recuperar_cursos')
def test_telemetria_caida_no_afecta_respuesta(mock_recuperar, mock_generar, mock_demanda, api_client):
    class DummyResult:
        id = 1
        provincia = 'León'
        titulo = 'Test'
        contenido = 'Test'
        url_oficial = 'Test'
        
    mock_recuperar.return_value = [DummyResult()]
    mock_generar.return_value = {"texto_respuesta": "Respuesta correcta", "fallback_activado": False}
    mock_demanda.side_effect = DatabaseError("DB Lock simulado")
    
    url = reverse('api_rag_ask')
    response = api_client.post(url, {'pregunta': 'Cursos'}, format='json')
    
    assert response.status_code == 200
    assert response.data['texto_respuesta'] == "Respuesta correcta"
    
@pytest.mark.django_db
def test_ratelimit_aislado_por_ip(api_client):
    url = reverse('api_rag_ask')
    
    # IP 1 realiza las 5 peticiones permitidas
    for _ in range(5):
        response = api_client.post(
            url, 
            {'pregunta': 'Test'}, 
            format='json', 
            HTTP_X_FORWARDED_FOR='192.168.1.50'
        )
        assert response.status_code != 429

    # La 6ª petición de la IP 1 debe ser bloqueada (429)
    response = api_client.post(
        url, 
        {'pregunta': 'Test'}, 
        format='json', 
        HTTP_X_FORWARDED_FOR='192.168.1.50'
    )
    assert response.status_code == 429

    # Una IP distinta debe pasar sin problemas a pesar del límite de la anterior
    response = api_client.post(
        url, 
        {'pregunta': 'Test'}, 
        format='json', 
        HTTP_X_FORWARDED_FOR='10.0.0.99'
    )
    assert response.status_code != 429