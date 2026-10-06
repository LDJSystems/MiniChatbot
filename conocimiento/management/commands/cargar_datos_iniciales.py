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

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _calcular_hash(url: str, titulo: str) -> str:
        """SHA-256 de url|titulo. Mismo criterio que ejecutar_etl para garantizar
        que ambos comandos identifiquen el mismo curso con el mismo hash."""
        clave = f"{(url or '').strip()}|{(titulo or '').strip()}"
        return hashlib.sha256(clave.encode('utf-8')).hexdigest()

    def _guardar(self, item: dict) -> None:
        """Inserta o actualiza un curso en staging a partir de un dict (fila JSON/CSV)."""
        hash_contenido = self._calcular_hash(item.get('url'), item.get('titulo'))
        campos = {
            'titulo_raw':        item.get('titulo'),
            'contenido_raw':     item.get('contenido'),
            'provincia_raw':     item.get('provincia'),
            'localidad':         item.get('localidad', ''),
            'campo_estudio_raw': item.get('campo_estudio'),
            'colectivo_raw':     item.get('colectivo'),
            'url_oficial':       item.get('url'),
        }
        StagingCursos.objects.update_or_create(
            hash_contenido=hash_contenido,
            defaults=campos,  # en UPDATE: refresca los datos, no toca 'estado'
            # En INSERT, create_defaults SUSTITUYE a defaults (no se combinan),
            # así que hay que repetir todos los campos y añadir el estado inicial.
            create_defaults={**campos, 'estado': StagingCursos.PENDIENTE},
        )

    # ── Cargadores ────────────────────────────────────────────────────────────

    @transaction.atomic
    def _cargar_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            self._guardar(item)
        self.stdout.write(self.style.SUCCESS(f"Procesados y guardados {len(data)} registros desde JSON en Staging."))

    @transaction.atomic
    def _cargar_csv(self, file_path):
        with open(file_path, mode='r', encoding='utf-8') as f:
            filas = list(csv.DictReader(f))
        for row in filas:
            self._guardar(row)
        self.stdout.write(self.style.SUCCESS(f"Procesados y guardados {len(filas)} registros desde CSV en Staging."))