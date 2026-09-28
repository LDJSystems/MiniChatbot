# operaciones/tests.py
from django.test import TestCase
from rest_framework import status
from .models import Lead

class LeadApiTests(TestCase):
    def setUp(self):
        self.url = '/api/chat/lead/'

    def test_crear_lead_exitoso(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "telefono": "+34600000000",
            "provincia": "Madrid",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": True
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertTrue(Lead.objects.first().consentimiento_rgpd)

    def test_rechazar_lead_sin_rgpd(self):
        data = {
            "nombre": "Lester Agramonte",
            "email": "lester@example.com",
            "provincia": "Madrid",
            "campo_estudio": "Informática",
            "colectivo": "General",
            "consentimiento_rgpd": False
        }
        response = self.client.post(self.url, data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Lead.objects.count(), 0)