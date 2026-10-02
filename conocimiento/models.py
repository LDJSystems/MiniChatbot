from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class BaseConocimiento(models.Model):
    class ProvinciaChoices(models.TextChoices):
        AVILA = 'Ávila', 'Ávila'
        BURGOS = 'Burgos', 'Burgos'
        LEON = 'León', 'León'
        PALENCIA = 'Palencia', 'Palencia'
        SALAMANCA = 'Salamanca', 'Salamanca'
        SEGOVIA = 'Segovia', 'Segovia'
        SORIA = 'Soria', 'Soria'
        VALLADOLID = 'Valladolid', 'Valladolid'
        ZAMORA = 'Zamora', 'Zamora'
        GENERAL = 'General', 'General/Nacional'
        ND = 'N/D', 'No Definido'

    class ColectivoChoices(models.TextChoices):
        DESEMPLEADOS = 'Desempleados', 'Desempleados'
        OCUPADOS = 'Ocupados', 'Trabajadores Ocupados'
        AUTONOMOS = 'Autónomos', 'Autónomos'
        JOVENES = 'Jóvenes', 'Garantía Juvenil'
        GENERAL = 'General', 'Público General'
    
    titulo = models.CharField(max_length=255)
    contenido = models.TextField()
    provincia = models.CharField(max_length=100, choices=ProvinciaChoices.choices, default=ProvinciaChoices.ND)
    localidad = models.CharField(max_length=100, blank=True, db_index=True)
    campo_estudio = models.CharField(max_length=100)
    colectivo = models.CharField(max_length=100, choices=ColectivoChoices.choices, default=ColectivoChoices.GENERAL)
    
    url_oficial = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    vector_busqueda = SearchVectorField(editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'base_conocimiento'
        indexes = [
            models.Index(fields=['provincia'], name='idx_bc_provincia'),
            models.Index(fields=['localidad'], name='idx_bc_localidad'),
            models.Index(fields=['campo_estudio'], name='idx_bc_campo'),
            models.Index(fields=['colectivo'], name='idx_bc_colectivo'),
            GinIndex(fields=['vector_busqueda'], name='idx_bc_fts_gin'),
        ]

class StagingCursos(models.Model):
    PENDIENTE  = 'pendiente'
    VALIDADO   = 'validado'
    PROCESADO  = 'procesado'
    ERROR      = 'error'

    ESTADO_CHOICES = [
        (PENDIENTE,  'Pendiente'),
        (VALIDADO,   'Validado'),
        (PROCESADO,  'Procesado'),
        (ERROR,      'Error'),
    ]

    titulo_raw = models.TextField()
    contenido_raw = models.TextField(blank=True, null=True)
    provincia_raw = models.TextField(blank=True, null=True)
    localidad = models.CharField(max_length=100, blank=True, db_index=True)
    campo_estudio_raw = models.TextField(blank=True, null=True)
    colectivo_raw = models.TextField(blank=True, null=True)
    url_oficial = models.TextField(blank=True, null=True, unique=True)
    hash_contenido = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=PENDIENTE)
    extraido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staging_cursos'
        indexes = [
            models.Index(fields=['estado'], name='idx_staging_estado'),
        ]