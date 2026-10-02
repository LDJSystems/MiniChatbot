import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from conocimiento.models import BaseConocimiento

class Command(BaseCommand):
    help = 'Carga inicial de datos desde un archivo JSON hacia BaseConocimiento.'

    def add_arguments(self, parser):
        parser.add_argument('archivo_json', type=str, help='Ruta al archivo JSON con los datos.')

    def handle(self, *args, **options):
        ruta_archivo = options['archivo_json']

        if not os.path.exists(ruta_archivo):
            raise CommandError(f"El archivo '{ruta_archivo}' no existe.")

        self.stdout.write(f"Leyendo datos desde {ruta_archivo}...")

        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"No se pudo leer el archivo JSON: {e}") from e

        creados = 0
        actualizados = 0

        try:
            with transaction.atomic():
                for item in datos:
                    _, created = BaseConocimiento.objects.update_or_create(
                        titulo=item.get('titulo'),
                        defaults={
                            'contenido':     item.get('contenido', ''),
                            'provincia':     item.get('provincia', 'General'),
                            'campo_estudio': item.get('campo_estudio', 'General'),
                            'colectivo':     item.get('colectivo', 'General'),
                            'activo':        item.get('activo', True),
                        }
                    )
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
        except Exception as e:
            raise CommandError(f"Error al escribir en base de datos: {e}") from e

        self.stdout.write(
            self.style.SUCCESS(
                f"Carga finalizada con éxito. Creados: {creados}, Actualizados: {actualizados}."
            )
        )