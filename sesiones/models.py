
from django.db import models
from django.db.models import Q
import uuid


class Sesion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    ultima_actividad = models.DateTimeField(auto_now=True)


class Mensaje(models.Model):

    class Rol(models.TextChoices):
        USER = 'user', 'Usuario'
        BOT = 'bot', 'Bot'

    sesion = models.ForeignKey(
        Sesion,
        on_delete=models.CASCADE,
        related_name='mensajes'
    )

    rol = models.CharField(max_length=20, choices=Rol.choices)
    contenido = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(rol__in=['user', 'bot']),
                name='mensaje_rol_valido'
            )
        ]
