import pytest
import asyncio
from django.urls import reverse
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_rag_endpoint_concurrency():
    """
    Valida que el endpoint /api/chat/ask/ soporte N peticiones concurrentes
    sin fallos de base de datos o bloqueos de hilo de Ollama.
    """
    url = "/api/chat/ask/"
    payload = {"query": "Consulta automática de catálogo"}
    
    # Simular 5 peticiones simultáneas
    concurrent_requests = 5
    
    async with AsyncClient(app=get_asgi_application(), base_url="http://testserver") as client:
        tasks = [
            client.post(url, json=payload)
            for _ in range(concurrent_requests)
        ]
        
        # Ejecutar en paralelo
        responses = await asyncio.gather(*tasks)
        
    for response in responses:
        # Falla si el servidor devuelve 500 (Ej: PostgreSQL 'too many clients' o timeout de Ollama)
        assert response.status_code == 200, f"Fallo de concurrencia detectado. Estado: {response.status_code}"
        
        data = response.json()
        assert "respuesta" in data, "La carga útil de respuesta no tiene el formato esperado."