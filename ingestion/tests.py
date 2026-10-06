# ingestion/tests.py
import pytest
from django.core.management import call_command
from conocimiento.models import BaseConocimiento, StagingCursos


@pytest.mark.django_db
def test_ejecutar_etl_command_success(capsys):
    """Valida que el ETL promueva cursos desde staging a BaseConocimiento.

    NOTA: este test hace scraping real de cefye.com. Cuando puedas, conviene
    mockear las peticiones HTTP para que no dependa de la red ni de la web.
    """
    call_command('ejecutar_etl')

    # Al promover, los cursos pasan a BaseConocimiento activos
    assert BaseConocimiento.objects.filter(activo=True).exists()

    # Ningún curso debe haber fallado en la promoción
    assert not StagingCursos.objects.filter(estado='error').exists()


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