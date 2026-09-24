import uuid
from django.db import models
from django.db.models import CheckConstraint, Q

class Sesion(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    campo_estudio = models.CharField(max_length=100, blank=True, null=True)
    colectivo = models.CharField(max_length=100, blank=True, null=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sesion'
        indexes = [
            models.Index(fields=['ultima_actividad'], name='idx_sesion_actividad'),
        ]

class Mensaje(models.Model):
    sesion = models.ForeignKey(Sesion, on_delete=models.CASCADE, db_column='sesion_uuid', to_field='uuid')
    rol = models.CharField(max_length=10)
    contenido = models.TextField()
    fallback_activado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mensaje'
        indexes = [
            models.Index(fields=['sesion'], name='idx_mensaje_sesion'),
        ]
        constraints = [
            CheckConstraint(condition=Q(rol__in=['user', 'bot']), name='chk_mensaje_rol')
        ]