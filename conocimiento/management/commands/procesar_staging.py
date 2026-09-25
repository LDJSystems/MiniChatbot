from django.core.management.base import BaseCommand
from django.db import transaction
from conocimiento.models import StagingCursos, BaseConocimiento

class Command(BaseCommand):
    help = 'Procesa los cursos pendientes de la tabla staging y los consolida en la base de conocimiento.'

    def handle(self, *args, **options):
        pendientes = StagingCursos.objects.filter(estado='pendiente')
        procesados = 0

        for curso in pendientes:
            try:
                with transaction.atomic():
                    # Evitar duplicados basados en contenido o URL si aplica, usando update_or_create
                    BaseConocimiento.objects.update_or_create(
                        url_oficial=curso.url_origen,
                        defaults={
                            'titulo': curso.titulo_raw,
                            'contenido': curso.contenido_raw or '',
                            'provincia': curso.provincia_raw or 'N/D',
                            'campo_estudio': curso.campo_estudio_raw or 'N/D',
                            'colectivo': curso.colectivo_raw or 'N/D',
                            'activo': True,
                        }
                    )
                    curso.estado = 'procesado'
                    curso.save(update_fields=['estado'])
                    procesados += 1
            except Exception as e:
                curso.estado = 'error'
                curso.save(update_fields=['estado'])
                self.stdout.write(self.style.ERROR(f"Error procesando curso ID {curso.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Proceso finalizado. Total procesados: {procesados}"))