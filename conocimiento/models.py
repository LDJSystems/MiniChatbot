from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class BaseConocimiento(models.Model):
    titulo = models.CharField(max_length=255)
    contenido = models.TextField()
    provincia = models.CharField(max_length=100)
    campo_estudio = models.CharField(max_length=100)
    colectivo = models.CharField(max_length=100)
    url_oficial = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    vector_busqueda = SearchVectorField(editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'base_conocimiento'
        indexes = [
            models.Index(fields=['provincia'], name='idx_bc_provincia'),
            models.Index(fields=['campo_estudio'], name='idx_bc_campo'),
            models.Index(fields=['colectivo'], name='idx_bc_colectivo'),
            GinIndex(fields=['vector_busqueda'], name='idx_bc_fts_gin'),
        ]

class StagingCursos(models.Model):
    titulo_raw = models.TextField()
    contenido_raw = models.TextField(blank=True, null=True)
    provincia_raw = models.TextField(blank=True, null=True)
    campo_estudio_raw = models.TextField(blank=True, null=True)
    colectivo_raw = models.TextField(blank=True, null=True)
    url_origen = models.TextField(blank=True, null=True)
    hash_contenido = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, default='pendiente')
    extraido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staging_cursos'
        indexes = [
            models.Index(fields=['estado'], name='idx_staging_estado'),
        ]