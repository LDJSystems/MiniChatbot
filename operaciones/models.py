from django.db import models
from django.db.models import CheckConstraint, Q

class Lead(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    provincia = models.CharField(max_length=100)
    campo_estudio = models.CharField(max_length=100)
    colectivo = models.CharField(max_length=100)
    consentimiento_rgpd = models.BooleanField()
    sesion_uuid = models.UUIDField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False)

    class Meta:
        db_table = 'lead'
        constraints = [
            CheckConstraint(condition=Q(email__isnull=False) | Q(telefono__isnull=False), name='chk_lead_contacto'),
            CheckConstraint(condition=Q(consentimiento_rgpd=True), name='chk_lead_rgpd'),
            CheckConstraint(condition=Q(provincia__isnull=False) & Q(campo_estudio__isnull=False) & Q(colectivo__isnull=False), name='chk_lead_contexto'),
        ]

class ConsultaFallida(models.Model):
    texto_consulta = models.TextField()
    provincia = models.CharField(max_length=100, blank=True, null=True)
    campo_estudio = models.CharField(max_length=100, blank=True, null=True)
    colectivo = models.CharField(max_length=100, blank=True, null=True)
    motivo_fallo = models.CharField(max_length=30)
    procesado = models.BooleanField(default=False)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consulta_fallida'
        indexes = [
            models.Index(fields=['procesado'], name='idx_cf_procesado'),
        ]

class ContadorDemanda(models.Model):
    base_conocimiento_id = models.BigIntegerField()
    provincia = models.CharField(max_length=100)
    campo_estudio = models.CharField(max_length=100)
    colectivo = models.CharField(max_length=100)
    total_consultas = models.IntegerField(default=1)
    ultima_consulta = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contador_demanda'
        constraints = [
            models.UniqueConstraint(
                fields=['base_conocimiento_id', 'provincia', 'campo_estudio', 'colectivo'],
                name='uq_contador_demanda'
            )
        ]
        indexes = [
            models.Index(fields=['base_conocimiento_id'], name='idx_contador_bc'),
        ]
        
class Provincia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=2, unique=True, blank=True, null=True)

    class Meta:
        db_table = 'provincia'
        verbose_name = 'Provincia'
        verbose_name_plural = 'Provincias'

    def __str__(self):
        return self.nombre


class Localidad(models.Model):
    nombre = models.CharField(max_length=150)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='localidades')

    class Meta:
        db_table = 'localidad'
        verbose_name = 'Localidad'
        verbose_name_plural = 'Localidades'
        unique_together = ('nombre', 'provincia')

    def __str__(self):
        return f"{self.nombre} ({self.provincia.nombre})"