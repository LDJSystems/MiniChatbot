# conocimiento/tests.py
import pytest
from django.db import connection
from django.contrib.postgres.search import SearchQuery
from django.urls import reverse
from conocimiento.models import BaseConocimiento, StagingCursos
from conocimiento.services import ChatbotKnowledgeService
import json
import tempfile
import os
from django.core.management import call_command

@pytest.mark.django_db
class TestTriggerVectorBusqueda:
    
    def test_vector_busqueda_generado_automaticamente(self):
        instancia = BaseConocimiento.objects.create(
            titulo="Introducción a Django ORM y PostgreSQL",
            contenido="Este documento explica el uso de triggers y full text search en bases de datos relacionales."
        )
        instancia.refresh_from_db()
        assert instancia.vector_busqueda is not None
        
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM base_conocimiento 
                WHERE id = %s AND vector_busqueda @@ plainto_tsquery('spanish', 'Django');
                """,
                [instancia.id]
            )
            resultado = cursor.fetchone()[0]
            
        assert resultado == 1

    def test_busqueda_full_text_por_relevancia(self):
        BaseConocimiento.objects.create(
            titulo="Django avanzado",
            contenido="Optimización de consultas y full text search con PostgreSQL.",
            provincia="Madrid",
            campo_estudio="Tecnología",
            colectivo="General"
        )
        
        query = SearchQuery('PostgreSQL', config='spanish')
        resultados = BaseConocimiento.objects.filter(vector_busqueda=query)
        
        assert resultados.exists()
        assert "PostgreSQL" in resultados.first().contenido
        
    def test_buscar_conocimiento_api(self, client):
        BaseConocimiento.objects.create(
            titulo="Django ORM Avanzado",
            contenido="Uso de índices GIN y full text search.",
            provincia="Madrid",
            campo_estudio="Tecnología",
            colectivo="General",
            activo=True
        )
        url = reverse('api_buscar_conocimiento')
        response = client.get(url, {'q': 'Django'})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['resultados']) > 0
        assert data['resultados'][0]['titulo'] == "Django ORM Avanzado"

@pytest.mark.django_db
def test_chatbot_knowledge_service_retrieval():
    BaseConocimiento.objects.create(
        titulo="Curso de Django Backend",
        contenido="Aprende desarrollo backend con Django y PostgreSQL.",
        provincia="Barcelona",
        campo_estudio="Informática",
        colectivo="Desempleados",
        url_oficial="https://ejemplo.com/django",
        activo=True
    )
    
    contexto = ChatbotKnowledgeService.recuperar_contexto("Django")
    
    assert "Curso de Django Backend" in contexto
    assert "Barcelona" in contexto
    assert "https://ejemplo.com/django" in contexto
    
@pytest.mark.django_db
def test_chatbot_query_api(client):
    BaseConocimiento.objects.create(
        titulo="Curso de Python",
        contenido="Aprende desarrollo web con Python y Django.",
        provincia="Madrid",
        campo_estudio="Tecnología",
        colectivo="General",
        activo=True
    )
    url = reverse('api_chatbot_query')
    response = client.post(
        url, 
        data=json.dumps({'pregunta': 'Python'}), 
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'Curso de Python' in data['contexto_utilizado']
    assert 'prompt_generado' in data

@pytest.mark.django_db
def test_cargar_datos_iniciales_command():
    datos_json = [
        {
            "hash_contenido": "hash_test_123",
            "titulo": "Curso Test Masivo",
            "contenido": "Contenido de prueba para staging.",
            "provincia": "Sevilla",
            "campo_estudio": "Tecnología",
            "colectivo": "Jóvenes",
            "url": "https://ejemplo.com/test-masivo"
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
        json.dump(datos_json, tf)
        tf_name = tf.name

    try:
        call_command('cargar_datos_iniciales', file=tf_name)
        assert StagingCursos.objects.filter(hash_contenido="hash_test_123").exists()
        staging = StagingCursos.objects.get(hash_contenido="hash_test_123")
        assert staging.titulo_raw == "Curso Test Masivo"
        assert staging.estado == "pendiente"
    finally:
        os.unlink(tf_name)