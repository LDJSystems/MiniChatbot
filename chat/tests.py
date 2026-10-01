import pytest
from django.urls import reverse
from rest_framework import status
from chat.models import Sesion, Mensaje

@pytest.mark.django_db
class ChatIntegrationTest:
    def test_creacion_sesion_y_mensajes(self):
        sesion = Sesion.objects.create(provincia="Madrid", campo_estudio="Informatica")
        
        msg_user = Mensaje.objects.create(
            sesion=sesion,
            rol="user",
            contenido="¿Qué cursos hay?",
            fallback_activado=False
        )
        
        msg_bot = Mensaje.objects.create(
            sesion=sesion,
            rol="bot",
            contenido="Hay cursos disponibles de Django.",
            fallback_activado=False
        )

        assert Mensaje.objects.filter(sesion=sesion).count() == 2
        assert msg_user.rol == "user"
        assert msg_bot.rol == "bot"