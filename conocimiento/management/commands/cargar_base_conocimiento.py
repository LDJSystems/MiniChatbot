# conocimiento/management/commands/cargar_base_conocimiento.py
import json
import os
from django.core.management.base import BaseCommand
from conocimiento.models import BaseConocimiento

class Command(BaseCommand):
    help = 'Carga inicial de datos desde un archivo JSON hacia BaseConocimiento.'

    def add_arguments(self, parser):
        parser.add_argument('archivo_json', type=str, help='Ruta al archivo JSON con los datos.')

    def handle(self, *args, **options):
        ruta_archivo = options['archivo_json']

        if not os.path.exists(ruta_archivo):
            self.stdout.write(self.style.ERROR(f"El archivo '{ruta_archivo}' no existe."))
            return

        self.stdout.write(f"Leyendo datos desde {ruta_archivo}...")

        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            creados = 0
            actualizados = 0

            for item in datos:
                titulo = item.get('titulo')
                contenido = item.get('contenido')
                provincia = item.get('provincia', 'General')
                campo_estudio = item.get('campo_estudio', 'General')
                colectivo = item.get('colectivo', 'General')
                activo = item.get('activo', True)

                _, created = BaseConocimiento.objects.update_or_create(
                    titulo=titulo,
                    defaults={
                        'contenido': contenido,
                        'provincia': provincia,
                        'campo_estudio': campo_estudio,
                        'colectivo': colectivo,
                        'activo': activo,
                    }
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Carga finalizada con éxito. Creados: {creados}, Actualizados: {actualizados}."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error procesando el archivo: {e}"))