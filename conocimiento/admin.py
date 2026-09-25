# conocimiento/admin.py
from django.contrib import admin
from .models import BaseConocimiento, StagingCursos

@admin.register(BaseConocimiento)
class BaseConocimientoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'provincia', 'campo_estudio', 'colectivo', 'activo', 'actualizado_en')
    list_filter = ('activo', 'provincia', 'campo_estudio', 'colectivo')
    search_fields = ('titulo', 'contenido')

@admin.register(StagingCursos)
class StagingCursosAdmin(admin.ModelAdmin):
    list_display = ('titulo_raw', 'estado', 'provincia_raw', 'campo_estudio_raw', 'extraido_en')
    list_filter = ('estado', 'provincia_raw', 'campo_estudio_raw')
    search_fields = ('titulo_raw', 'contenido_raw')