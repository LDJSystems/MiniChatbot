from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from sesiones.models import Sesion, Mensaje


class PurgarSesionesTest(TestCase):
    def test_cascade_elimina_mensajes_sin_n_plus_one(self):
        # Sesión vieja (se borrará)
        sesion_vieja = Sesion.objects.create()
        Sesion.objects.filter(id=sesion_vieja.id).update(
            ultima_actividad=timezone.now() - timedelta(hours=2)
        )

        # 50 mensajes para “detectar” N+1 si Django borrara fila por fila con consultas
        Mensaje.objects.bulk_create([
            Mensaje(
                sesion=sesion_vieja,
                rol='user' if i % 2 == 0 else 'bot',
                contenido=f"m{i}"
            )
            for i in range(50)
        ])

        # Sesión activa (no se borra)
        sesion_activa = Sesion.objects.create()
        Mensaje.objects.create(
            sesion=sesion_activa,
            rol='user',
            contenido="activo"
        )

        threshold = timezone.now() - timedelta(hours=1)

        with CaptureQueriesContext(connection) as queries:
            Sesion.objects.filter(ultima_actividad__lt=threshold).delete()

        # Validación CASCADE (PostgreSQL + FK CASCADE)
        self.assertEqual(Mensaje.objects.filter(sesion_id=sesion_vieja.id).count(), 0)
        self.assertEqual(Mensaje.objects.filter(sesion_id=sesion_activa.id).count(), 1)

        # Validación anti N+1: el conteo de queries no debería dispararse con 50 mensajes.
        # Ajusta el umbral si en tu entorno ves 3-5 queries extra.
        self.assertLessEqual(
            len(queries),
            5,
            f"Posible N+1 / demasiadas consultas durante el delete: {len(queries)}"
        )
