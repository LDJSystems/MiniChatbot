from django.contrib import admin

from .models import ConsultaFallida, ContadorDemanda


@admin.action(description="Marcar consultas seleccionadas como procesadas")
def marcar_como_procesadas(modeladmin, request, queryset):
    queryset.update(procesado=True)


@admin.register(ConsultaFallida)
class ConsultaFallidaAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "motivo_fallo",
        "procesado",
        "creado_en",
    ]

    list_filter = [
        "procesado",
        "creado_en",
    ]

    search_fields = [
        "motivo_fallo",
    ]

    actions = [
        marcar_como_procesadas,
    ]

    ordering = [
        "-creado_en",
    ]


@admin.register(ContadorDemanda)
class ContadorDemandaAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "base_conocimiento_id",
        "demanda",
        "actualizado_en",
    ]

    list_filter = [
        "base_conocimiento_id",
    ]

    search_fields = [
        "base_conocimiento_id",
    ]

    ordering = [
        "-demanda",
    ]