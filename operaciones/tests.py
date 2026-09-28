# operaciones/tests.py
from django.test import TestCase
from rest_framework import status
from .models import Lead, Provincia, Localidad

class LeadApiTests(TestCase):
    def setUp(self):
        self.url = '/api/lead/'
        provincias_cyl = ["Ávila", "Burgos", "León", "Palencia", "Salamanca", "Segovia", "Soria", "Valladolid", "Zamora"]
        for p in provincias_cyl:
            prov, _ = Provincia.objects.get_or_create(nombre=p)
            if p == "León":
                Localidad.objects.get_or_create(nombre="Ponferrada", provincia=prov)
            elif p == "Burgos":
                Localidad.objects.get_or_create(nombre="Burgos", provincia=prov)

    def test_crear_lead_exitoso(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "telefono": "+34600000000",
            "provincia": "Valladolid",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": True
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertTrue(Lead.objects.first().consentimiento_rgpd)

    def test_rechazar_lead_provincia_invalida(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "provincia": "Madrid",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": True
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Lead.objects.count(), 0)

    def test_rechazar_lead_sin_rgpd(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "provincia": "León",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": False
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Lead.objects.count(), 0)

    def test_crear_lead_con_localidad_valida(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "provincia": "León",
            "localidad": "Ponferrada",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": True
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_rechazar_lead_localidad_no_pertenece_a_provincia(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "provincia": "León",
            "localidad": "Burgos",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": True
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Lead.objects.count(), 0)