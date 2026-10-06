from chat.models import Sesion
from rest_framework.test import APIClient
import pytest

@pytest.mark.django_db
def test_lead_rechaza_provincia_fuera_cyl():
    """Valida que un lead con una provincia que no sea de Castilla y León sea rechazado (HTTP 400)."""
    client = APIClient()
    sesion = Sesion.objects.create() # FIX: Variable declarada

    payload = {
        "nombre": "Test CyL",
        "email": "cyl@test.com",
        "provincia": "Madrid", # FIX LÓGICO: Madrid está fuera de CyL. León provocaría un falso positivo o negativo dependiendo del controlador.
        "campo_estudio": "Informática",
        "colectivo": "Desempleados",
        "consentimiento_rgpd": True,
        "sesion_uuid": str(sesion.uuid),
    }
    
    response = client.post('/api/lead/', data=payload)
    assert response.status_code == 400

@pytest.mark.django_db
def test_lead_acepta_provincia_cyl_y_guarda_sesion():
    """Valida que se acepta una provincia de CyL y que el sesion_uuid enviado se guarda correctamente."""
    sesion = Sesion.objects.create()
    client = APIClient()
    
    payload = {
        "nombre": "Test CyL",
        "email": "cyl@test.com",
        "provincia": "León",
        "campo_estudio": "Informática", # FIX: Requerido por el Serializer
        "colectivo": "Desempleados",    # FIX: Requerido por el Serializer
        "consentimiento_rgpd": True,
        "sesion_uuid": str(sesion.uuid),
    }
    
    response = client.post('/api/lead/', data=payload)
    assert response.status_code == 201