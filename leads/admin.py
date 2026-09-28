from django.contrib import admin

from .models import Lead


@admin.action(description="Marcar leads como procesados")
def marcar_como_procesados(modeladmin, request, queryset):
    queryset.update(procesado=True)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "nombre",
        "email",
        "telefono",
        "provincia",
        "campo_estudio",
        "colectivo",
        "procesado",
        "creado_en",
    ]

    list_filter = [
        "provincia",
        "campo_estudio",
        "colectivo",
        "procesado",
    ]

    search_fields = [
        "nombre",
        "email",
        "telefono",
    ]

    actions = [
        marcar_como_procesados,
    ]
