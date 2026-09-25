from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from datetime import timedelta

from sesiones.models import Sesion, Mensaje


class CascadePurgaTest(TestCase):
    def test_purgar_sesiones_inactivas_cascade_elimina_mensajes_sin_n_plus_one(self):
        # Sesión vieja (debe borrarse) + muchas filas de Mensaje
        sesion_vieja = Sesion.objects.create(ultima_actividad=timezone.now() - timedelta(hours=2))
        mensajes = []
        for i in range(50):
            mensajes.append(Mensaje(sesion=sesion_vieja, rol='user' if i % 2 == 0 else 'bot', contenido=f"m{i}"))

        Mensaje.objects.bulk_create(mensajes)

        # Sesión activa (NO debe borrarse)
        sesion_activa = Sesion.objects.create(ultima_actividad=timezone.now())
        Mensaje.objects.create(sesion=sesion_activa, rol='user', contenido="activo")

        # Capturamos queries solo para el bloque del delete
        threshold = timezone.now() - timedelta(hours=1)
        with CaptureQueriesContext(connection) as queries:
            Sesion.objects.filter(ultima_actividad__lt=threshold).delete()

        # Verificación: mensajes de vieja sesión deben desaparecer
        self.assertEqual(Mensaje.objects.filter(sesion_id=sesion_vieja.id).count(), 0)
        self.assertEqual(Mensaje.objects.filter(sesion_id=sesion_activa.id).count(), 1)

        # “N+1” típico dispararía muchas queries (una por cada mensaje).
        # Un umbral conservador: si el ORM borrara mensaje por mensaje, crecería con 50.
        self.assertLessEqual(len(queries), 5, f"Demasiadas queries detectadas: {len(queries)}")
