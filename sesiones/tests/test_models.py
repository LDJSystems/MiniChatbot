from threading import Event, Thread

from django.db import connection
from django.test import CaptureQueriesContext, TestCase, TransactionTestCase

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

    def test_cascade_no_generar_n_plus_one_al_borrar(self):
        sesion = Sesion.objects.create()

        for i in range(20):
            Mensaje.objects.create(
                sesion=sesion,
                rol="user" if i % 2 == 0 else "bot",
                contenido=f"msg {i}",
            )

        with CaptureQueriesContext(connection) as queries:
            sesion.delete()

        self.assertLessEqual(
            len(queries),
            2,
            f"Se ejecutaron demasiadas consultas: {len(queries)}",
        )


class SesionConcurrenciaTest(TransactionTestCase):

    def test_actualizar_ultima_actividad_no_bloquea_concurrente(self):
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

        self.assertFalse(
            t1.is_alive(),
            "El primer worker quedó bloqueado.",
        )

        self.assertFalse(
            t2.is_alive(),
            "El segundo worker quedó bloqueado.",
        )

        self.assertFalse(
            errors,
            f"Errores en workers: {errors}",
        )

        self.assertEqual(
            len(done),
            2,
            "Uno o ambos workers no terminaron.",
        )