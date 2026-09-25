import json
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from conocimiento.models import StagingCursos

class Command(BaseCommand):
    help = 'Carga masiva de cursos en la tabla staging desde un archivo JSON o CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Ruta absoluta o relativa al archivo JSON o CSV')

    def handle(self, *args, **options):
        file_path = options['file']
        if file_path.endswith('.json'):
            self._cargar_json(file_path)
        elif file_path.endswith('.csv'):
            self._cargar_csv(file_path)
        else:
            self.stdout.write(self.style.ERROR("Formato de archivo no soportado. Debe ser .json o .csv"))

    @transaction.atomic
    def _cargar_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            contador = 0
            for item in data:
                StagingCursos.objects.update_or_create(
                    hash_contenido=item.get('hash_contenido'),
                    defaults={
                        'titulo_raw': item.get('titulo'),
                        'contenido_raw': item.get('contenido'),
                        'provincia_raw': item.get('provincia'),
                        'campo_estudio_raw': item.get('campo_estudio'),
                        'colectivo_raw': item.get('colectivo'),
                        'url_origen': item.get('url'),
                        'estado': 'pendiente'
                    }
                )
                contador += 1
        self.stdout.write(self.style.SUCCESS(f"Procesados y guardados {contador} registros desde JSON en Staging."))

    @transaction.atomic
    def _cargar_csv(self, file_path):
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            contador = 0
            for row in reader:
                StagingCursos.objects.update_or_create(
                    hash_contenido=row.get('hash_contenido'),
                    defaults={
                        'titulo_raw': row.get('titulo'),
                        'contenido_raw': row.get('contenido'),
                        'provincia_raw': row.get('provincia'),
                        'campo_estudio_raw': row.get('campo_estudio'),
                        'colectivo_raw': row.get('colectivo'),
                        'url_origen': row.get('url'),
                        'estado': 'pendiente'
                    }
                )
                contador += 1
        self.stdout.write(self.style.SUCCESS(f"Procesados y guardados {contador} registros desde CSV en Staging."))