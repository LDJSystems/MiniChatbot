# ingestion/tests.py
import pytest
from django.core.management import call_command
from django.db import transaction
from conocimiento.models import BaseConocimiento, StagingCursos

@pytest.mark.django_db
def test_ejecutar_etl_command_success(capsys):
    """Valida que el comando de gestión procese los registros correctamente desde staging a producción"""
    # Ejecutar el comando de gestión
    call_command('ejecutar_etl')

    # Verificar que el registro se creó en staging y pasó a estado 'validado'
    assert StagingCursos.objects.filter(estado='validado').exists()
    
    # Verificar que se insertó o actualizó en BaseConocimiento
    assert BaseConocimiento.objects.filter(titulo="Curso Avanzado de Django").exists()

@pytest.mark.django_db
def test_staging_hash_unicidad():
    """Valida que el hash evite duplicados físicos en el buffer de staging"""
    hash_test = "hashduplicadotest123"
    
    StagingCursos.objects.create(
        titulo_raw="Curso Original",
        contenido_raw="Contenido único",
        hash_contenido=hash_test,
        estado="pendiente"
    )

    with pytest.raises(Exception):
        StagingCursos.objects.create(
            titulo_raw="Curso Duplicado",
            contenido_raw="Contenido único duplicado",
            hash_contenido=hash_test,
            estado="pendiente"
        )