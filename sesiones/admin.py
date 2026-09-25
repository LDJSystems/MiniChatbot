from django.contrib import admin
from django.db.models import Count

from .models import Sesion, Mensaje


@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = ("id", "ultima_actividad", "mensajes_count")
    readonly_fields = ("id", "ultima_actividad")
    ordering = ("-ultima_actividad",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(mensajes_count=Count("mensajes"))

    def mensajes_count(self, obj):
        return obj.mensajes_count

    mensajes_count.short_description = "Mensajes"

    # solo lectura (bloquea CRUD)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ("id", "sesion", "rol", "contenido")
    list_select_related = ("sesion",)
    readonly_fields = ("id", "sesion", "rol", "contenido")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
