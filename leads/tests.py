from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Lead


class LeadAPITests(APITestCase):

    url = "/api/chat/lead/"

    def datos_validos(self):
        return {
            "nombre": "Ana Pérez",
            "email": "ana@example.com",
            "telefono": "600123456",
            "provincia": "León",
            "campo_estudio": "Laboratorio",
            "colectivo": "Estudiante",
            "consentimiento_rgpd": True,
        }

    def test_no_se_puede_crear_lead_sin_email_ni_telefono(self):
        data = self.datos_validos()

        data["email"] = ""
        data["telefono"] = ""

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Lead.objects.count(),
            0,
        )

    def test_no_se_puede_crear_lead_sin_consentimiento_rgpd(self):
        data = self.datos_validos()

        data["consentimiento_rgpd"] = False

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Lead.objects.count(),
            0,
        )

    def test_se_puede_crear_lead_con_email(self):
        data = self.datos_validos()

        data["telefono"] = ""

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Lead.objects.count(),
            1,
        )

    def test_se_puede_crear_lead_con_telefono(self):
        data = self.datos_validos()

        data["email"] = ""

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Lead.objects.count(),
            1,
        )