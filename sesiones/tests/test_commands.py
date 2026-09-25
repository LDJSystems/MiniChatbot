from django.test import TestCase
from chat.models import Sesion, Mensaje


class SesionCascadeTest(TestCase):

    def test_eliminar_sesion_elimina_mensajes(self):
        sesion = Sesion.objects.create()

        Mensaje.objects.create(
            sesion=sesion,
            rol="user",
            contenido="Hola",
        )

        Mensaje.objects.create(
            sesion=sesion,
            rol="assistant",
            contenido="Hola, ¿cómo estás?",
        )

        self.assertEqual(Mensaje.objects.filter(sesion=sesion).count(), 2)

        sesion.delete()

        self.assertEqual(Mensaje.objects.filter(sesion_id=sesion.id).count(), 0)