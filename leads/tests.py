import pytest
from rest_framework.test import APIClient
from leads.models import Lead

@pytest.mark.django_db
def test_lead_rechaza_provincia_fuera_cyl():
    """Valida que un lead con una provincia que no sea de Castilla y León sea rechazado (HTTP 400)."""
    client = APIClient()
    payload = {
        "nombre": "Test Fuera",
        "email": "fuera@test.com",
        "provincia": "Madrid", # No es CyL
        "localidad": "Madrid",
        "lopd_aceptada": True
    }
    
    response = client.post('/api/lead/', data=payload)
    
    # Debe fallar, no debe crearse el lead
    assert response.status_code == 400
    assert "provincia" in response.data
    assert Lead.objects.count() == 0

@pytest.mark.django_db
def test_lead_acepta_provincia_cyl_y_guarda_sesion():
    """Valida que se acepta una provincia de CyL y que el sesion_uuid enviado se guarda correctamente."""
    from chat.models import Sesion
    # Creamos una sesión real para el test
    sesion = Sesion.objects.create()
    
    client = APIClient()
    payload = {
        "nombre": "Test CyL",
        "email": "cyl@test.com",
        "provincia": "León", # Sí es CyL
        "localidad": "Ponferrada",
        "lopd_aceptada": True,
        "sesion_uuid": str(sesion.uuid) # Simulamos el envío desde el widget
    }
    
    response = client.post('/api/lead/', data=payload)
    
    # Debe pasar exitosamente
    assert response.status_code == 201
    lead_creado = Lead.objects.first()
    assert lead_creado.provincia == "León"
    # El sesion_uuid debe haberse guardado, no ignorado
    assert lead_creado.sesion_uuid == str(sesion.uuid)
    
def test_rechaza_provincia_fuera_cyl(self):
        data = self.datos_validos()
        data["provincia"] = "Madrid"
        
        response = self.client.post(self.url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("provincia", response.data)
        self.assertEqual(Lead.objects.count(), 0)