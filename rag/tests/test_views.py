import pytest
from rest_framework.test import APIClient
from django.core.cache import cache

@pytest.fixture(autouse=True)
def clear_cache():
    """Limpia la base de datos o en memoria de caché antes de cada test 
    para aislar el estado del Rate Limit."""
    cache.clear()

@pytest.mark.django_db
def test_rate_limit_rechaza_rafagas():
    """
    Valida que la vista síncrona rechaza la sexta petición desde la misma IP
    (simulando la cabecera del proxy X-Forwarded-For) devolviendo HTTP 429.
    """
    client = APIClient()
    url = '/api/chat/ask/'
    payload = {"pregunta": "¿Qué cursos hay en León?"}
    headers = {"HTTP_X_FORWARDED_FOR": "192.168.1.100"}

    # Ejecutar 5 peticiones permitidas (límite configurado a 5/m)
    for i in range(5):
        resp = client.post(url, payload, format='json', **headers)
        # El test debe tolerar 200 (éxito/fallback) o 500 (Ollama offline temporalmente)
        # Lo crítico es que la petición no sea rechazada prematuramente por el limitador.
        assert resp.status_code in [200, 500], f"Fallo prematuro en iteración {i+1}. Estado: {resp.status_code}"

    # La sexta petición debe ser bloqueada estrictamente por el Rate Limiter
    resp_bloqueada = client.post(url, payload, format='json', **headers)
    
    assert resp_bloqueada.status_code == 429, f"El Rate Limit falló con código {resp_bloqueada.status_code}."
    
    data = resp_bloqueada.json()
    assert "detail" in data, "La respuesta 429 no contiene la clave 'detail' de DRF."
    assert "regulada" in data["detail"] or "throttled" in data["detail"].lower()