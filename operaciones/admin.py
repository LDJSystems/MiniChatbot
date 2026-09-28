# operaciones/admin.py
from django.contrib import admin
from .models import Lead, ConsultaFallida, ContadorDemanda, Provincia, Localidad

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre',)


@admin.register(Localidad)
class LocalidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'provincia')
    list_filter = ('provincia',)
    search_fields = ('nombre', 'provincia__nombre')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'telefono', 'provincia', 'localidad', 'campo_estudio', 'colectivo', 'consentimiento_rgpd', 'procesado', 'creado_en')
    list_filter = ('provincia', 'campo_estudio', 'colectivo', 'consentimiento_rgpd', 'procesado')
    search_fields = ('nombre', 'email', 'telefono')
    readonly_fields = ('creado_en',)
    ordering = ('-creado_en',)


@admin.register(ConsultaFallida)
class ConsultaFallidaAdmin(admin.ModelAdmin):
    list_display = ('texto_consulta', 'provincia', 'campo_estudio', 'colectivo', 'motivo_fallo', 'procesado', 'registrado_en')
    list_filter = ('provincia', 'campo_estudio', 'colectivo', 'procesado', 'registrado_en')
    search_fields = ('texto_consulta',)
    readonly_fields = ('texto_consulta', 'provincia', 'campo_estudio', 'colectivo', 'motivo_fallo', 'registrado_en')
    ordering = ('-registrado_en',)

    def has_add_permission(self, request):
        return False


@admin.register(ContadorDemanda)
class ContadorDemandaAdmin(admin.ModelAdmin):
    list_display = ('base_conocimiento_id', 'provincia', 'campo_estudio', 'colectivo', 'total_consultas', 'ultima_consulta')
    list_filter = ('provincia', 'campo_estudio', 'colectivo')
    search_fields = ('base_conocimiento_id',)
    readonly_fields = ('base_conocimiento_id', 'provincia', 'campo_estudio', 'colectivo', 'total_consultas', 'ultima_consulta')
    ordering = ('-total_consultas',)

    def has_add_permission(self, request):
        return False