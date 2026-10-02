import json
import csv
import hashlib
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

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _calcular_hash(url: str, titulo: str) -> str:
        """SHA-256 de url|titulo. Mismo criterio que ejecutar_etl para garantizar
        que ambos comandos identifiquen el mismo curso con el mismo hash."""
        clave = f"{(url or '').strip()}|{(titulo or '').strip()}"
        return hashlib.sha256(clave.encode('utf-8')).hexdigest()

    # ── Cargadores ────────────────────────────────────────────────────────────

    @transaction.atomic
    def _cargar_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            contador = 0
            for item in data:
                hash_contenido = self._calcular_hash(
                    item.get('url'), item.get('titulo')
                )
                StagingCursos.objects.update_or_create(
                    hash_contenido=hash_contenido,
                    defaults={
                        'titulo_raw':        item.get('titulo'),
                        'contenido_raw':     item.get('contenido'),
                        'provincia_raw':     item.get('provincia'),
                        'localidad':         item.get('localidad', ''),
                        'campo_estudio_raw': item.get('campo_estudio'),
                        'colectivo_raw':     item.get('colectivo'),
                        'url_origen':        item.get('url'),
                    },
                    create_defaults={
                        'estado': StagingCursos.PENDIENTE,  # solo en INSERT, nunca machaca
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
                hash_contenido = self._calcular_hash(
                    row.get('url'), row.get('titulo')
                )
                StagingCursos.objects.update_or_create(
                    hash_contenido=hash_contenido,
                    defaults={
                        'titulo_raw':        row.get('titulo'),
                        'contenido_raw':     row.get('contenido'),
                        'provincia_raw':     row.get('provincia'),
                        'localidad':         row.get('localidad', ''),
                        'campo_estudio_raw': row.get('campo_estudio'),
                        'colectivo_raw':     row.get('colectivo'),
                        'url_origen':        row.get('url'),
                    },
                    create_defaults={
                        'estado': StagingCursos.PENDIENTE,  # solo en INSERT, nunca machaca
                    }
                )
                contador += 1
        self.stdout.write(self.style.SUCCESS(f"Procesados y guardados {contador} registros desde CSV en Staging."))