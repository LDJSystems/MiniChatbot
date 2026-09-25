from datetime import timedelta
from threading import Event, Thread

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from sesiones.models import Sesion, Mensaje
from sesiones.services import crear_o_recuperar_sesion


class MensajeCascadeTest(TestCase):

    def test_al_borrar_sesion_se_borran_sus_mensajes(self):
        sesion = Sesion.objects.create()

        Mensaje.objects.create(
            sesion=sesion,
            rol="user",
            contenido="Hola",
        )

        Mensaje.objects.create(
            sesion=sesion,
            rol="bot",
            contenido="Hola, ¿cómo estás?",
        )

        self.assertEqual(
            Mensaje.objects.filter(sesion=sesion).count(),
            2,
        )

        sesion.delete()

        self.assertEqual(
            Mensaje.objects.filter(sesion_id=sesion.id).count(),
            0,
        )

    def test_cascade_no_genera_n_plus_one_al_borrar(self):
        sesion = Sesion.objects.create()

        Mensaje.objects.bulk_create([
            Mensaje(
                sesion=sesion,
                rol="user" if i % 2 == 0 else "bot",
                contenido=f"msg {i}",
            )
            for i in range(20)
        ])

        with CaptureQueriesContext(connection) as queries:
            sesion.delete()

        self.assertLessEqual(
            len(queries),
            5,
            f"Demasiadas consultas: {len(queries)}",
        )


class PurgarSesionesTest(TestCase):

    def test_purgar_sesiones_inactivas_elimina_mensajes(self):
        sesion_vieja = Sesion.objects.create()

        Sesion.objects.filter(id=sesion_vieja.id).update(
            ultima_actividad=timezone.now() - timedelta(hours=2)
        )

        Mensaje.objects.bulk_create([
            Mensaje(
                sesion=sesion_vieja,
                rol="user" if i % 2 == 0 else "bot",
                contenido=f"m{i}",
            )
            for i in range(50)
        ])

        sesion_activa = Sesion.objects.create()

        Mensaje.objects.create(
            sesion=sesion_activa,
            rol="user",
            contenido="activo",
        )

        threshold = timezone.now() - timedelta(hours=1)

        with CaptureQueriesContext(connection) as queries:
            Sesion.objects.filter(
                ultima_actividad__lt=threshold
            ).delete()

        self.assertEqual(
            Mensaje.objects.filter(
                sesion_id=sesion_vieja.id
            ).count(),
            0,
        )

        self.assertEqual(
            Mensaje.objects.filter(
                sesion_id=sesion_activa.id
            ).count(),
            1,
        )

        self.assertLessEqual(
            len(queries),
            5,
            f"Demasiadas consultas: {len(queries)}",
        )


class SesionConcurrenciaTest(TransactionTestCase):

    def test_actualizar_ultima_actividad_no_bloquea(self):
        sesion = Sesion.objects.create()
        session_id = sesion.id

        start = Event()
        done = []
        errors = []

        def worker():
            try:
                start.wait(timeout=2)
                crear_o_recuperar_sesion(session_id)
                done.append(True)
            except Exception as error:
                errors.append(error)

        t1 = Thread(target=worker)
        t2 = Thread(target=worker)

        t1.start()
        t2.start()

        start.set()

        t1.join(timeout=3)
        t2.join(timeout=3)

        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertFalse(errors)
        self.assertEqual(len(done), 2)