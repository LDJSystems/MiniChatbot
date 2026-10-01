import pytest
from unittest.mock import patch
from requests.exceptions import Timeout, ConnectionError
from rag.generator import generar_respuesta_ia

@pytest.mark.django_db
@patch('rag.generator.requests.post')
def test_generator_maneja_timeout_ollama(mock_post):
    mock_post.side_effect = Timeout("Ollama timeout")
    
    resultado = generar_respuesta_ia("pregunta de prueba", [{"titulo": "Curso", "contenido": "Contenido", "url_oficial": None}])
    assert resultado["fallback_activado"] is True
    assert "saturado" in resultado["texto_respuesta"].lower() or "error" in resultado["texto_respuesta"].lower()

@pytest.mark.django_db
@patch('rag.generator.requests.post')
def test_generator_maneja_connection_error(mock_post):
    mock_post.side_effect = ConnectionError("Connection refused")
    
    resultado = generar_respuesta_ia("pregunta de prueba", [{"titulo": "Curso", "contenido": "Contenido", "url_oficial": None}])
    assert resultado["fallback_activado"] is True