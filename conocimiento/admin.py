from django.contrib import admin
from django.contrib import messages
from .models import BaseConocimiento, StagingCursos
from .services import promover_staging


@admin.register(BaseConocimiento)
class BaseConocimientoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'provincia', 'campo_estudio', 'colectivo', 'activo', 'actualizado_en')
    list_filter = ('activo', 'provincia', 'campo_estudio', 'colectivo')
    search_fields = ('titulo', 'contenido')
    readonly_fields = ('vector_busqueda', 'actualizado_en')

    actions = ['marcar_inactivos', 'marcar_activos']

    @admin.action(description="Marcar cursos seleccionados como inactivos")
    def marcar_inactivos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} cursos marcados como inactivos.")

    @admin.action(description="Marcar cursos seleccionados como activos")
    def marcar_activos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} cursos marcados como activos.")


@admin.register(StagingCursos)
class StagingCursosAdmin(admin.ModelAdmin):
    list_display = ('titulo_raw', 'estado_badge', 'provincia_raw', 'campo_estudio_raw', 'extraido_en')
    list_filter = ('estado', 'provincia_raw', 'campo_estudio_raw')
    search_fields = ('titulo_raw', 'contenido_raw')
    readonly_fields = ('hash_contenido', 'extraido_en')

    actions = ['procesar_staging_seleccionados']

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return obj.estado.upper()

    @admin.action(description="Procesar y pasar a producción los registros seleccionados")
    def procesar_staging_seleccionados(self, request, queryset):
        resultado = promover_staging(queryset=queryset)

        level = messages.SUCCESS if not resultado['errores'] else messages.WARNING
        self.message_user(
            request,
            f"Procesados: {resultado['procesados']}. Errores: {resultado['errores']}."
            + (f" IDs con error: {resultado['ids_error']}" if resultado['errores'] else ""),
            level=level,
        )