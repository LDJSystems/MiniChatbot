import pytest
from rag.retriever import recuperar_cursos
from conocimiento.models import BaseConocimiento

@pytest.mark.django_db
class TestRetriever:
    
    def test_sin_resultados_devuelve_lista_vacia(self):
        """Valida la eliminación del fallback global para habilitar derivación a humano."""
        BaseConocimiento.objects.create(
            titulo="Curso de Kubernetes",
            localidad="Zamora",
            provincia="Zamora",
            activo=True,
            vector_busqueda="kubernetes"
        )
        
        resultados = recuperar_cursos("Curso de cocina en Soria")
        # Si el fallback global sigue existiendo, devolverá el curso de Kubernetes. Debe ser [].
        assert resultados == [], "El retriever debe devolver [] al no encontrar coincidencias para escalar al agente."

    def test_localidad_iexact_evita_falsos_positivos(self):
        """Valida que buscar 'León' no devuelva cursos de localidades que contengan la palabra pero no sean exactamente esa."""
        BaseConocimiento.objects.create(
            titulo="Curso de Soldadura",
            localidad="Pantón (León)", # Falso positivo potencial con icontains
            provincia="Lugo",
            activo=True,
            vector_busqueda="soldadura"
        )
        BaseConocimiento.objects.create(
            titulo="Curso de Python",
            localidad="León",
            provincia="León",
            activo=True,
            vector_busqueda="python"
        )
        
        # Filtro estricto geográfico sin término de búsqueda válido
        resultados = recuperar_cursos("formacion en León")
        
        assert len(resultados) == 1, "Debe devolver únicamente el curso de León exacto."
        assert resultados[0].localidad == "León"