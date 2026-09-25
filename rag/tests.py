# rag/tests.py
import pytest
from unittest.mock import patch, MagicMock
import json
from django.urls import reverse
from django.core.cache import cache
from conocimiento.models import BaseConocimiento
from rag.retriever import recuperar_cursos
from rag.generator import generar_respuesta_ia

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()

@pytest.mark.django_db
@patch('django.contrib.postgres.search.SearchRank', return_value=0.05)
def test_retriever_umbral_fallback(mock_rank):
    BaseConocimiento.objects.create(
        titulo="Curso de Prueba",
        contenido="Contenido irrelevante o con baja coincidencia.",
        activo=True
    )
    
    resultados = recuperar_cursos("consulta de prueba")
    assert len(resultados) == 0, "El retriever no debe retornar elementos con rank menor al umbral"

@pytest.mark.django_db
def test_generator_fallback_sin_resultados():
    respuesta = generar_respuesta_ia("pregunta", [])
    assert respuesta["fallback_activado"] is True
    assert respuesta["requiere_accion_comercial"] is True
    assert "no he encontrado información" in respuesta["texto_respuesta"]

@pytest.mark.django_db
@patch('rag.generator.requests.post')
def test_generator_ollama_exitoso(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Respuesta generada por Ollama."}
    mock_post.return_value = mock_response

    class DummyResult:
        titulo = "Curso"
        contenido = "Contenido"
        url_oficial = None

    respuesta = generar_respuesta_ia("pregunta", [DummyResult()])
    assert respuesta["fallback_activado"] is False
    assert respuesta["texto_respuesta"] == "Respuesta generada por Ollama."

@pytest.mark.django_db
@patch('rag.views.recuperar_cursos')
@patch('rag.generator.requests.post')
def test_chat_ask_endpoint(mock_post, mock_recuperar, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Respuesta simulada del LLM."}
    mock_post.return_value = mock_response

    class DummyResult:
        titulo = "Curso de Django"
        contenido = "Contenido avanzado de Django y Python."
        url_oficial = "https://example.com"

    mock_recuperar.return_value = [DummyResult()]

    url = reverse('api_rag_ask')
    response = client.post(
        url,
        data=json.dumps({"pregunta": "Django", "filtros": {"provincia": "Madrid"}}),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = response.json()
    assert "texto_respuesta" in data
    assert "requiere_accion_comercial" in data
    assert "fallback_activado" in data
    assert data["fallback_activado"] is False

@pytest.mark.django_db
@patch('rag.generator.requests.post')
@patch('rag.views.recuperar_cursos', return_value=[])
def test_chat_ask_rate_limit(mock_recuperar, mock_post, client):
    url = reverse('api_rag_ask')
    
    for _ in range(5):
        client.post(
            url,
            data=json.dumps({"pregunta": "Django"}),
            content_type='application/json'
        )

    response = client.post(
        url,
        data=json.dumps({"pregunta": "Django"}),
        content_type='application/json'
    )
    assert response.status_code == 429