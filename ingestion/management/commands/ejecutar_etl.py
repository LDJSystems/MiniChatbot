# ingestion/management/commands/ejecutar_etl.py
import hashlib
import logging
from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError
from conocimiento.models import BaseConocimiento, StagingCursos

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Pipeline ETL robusto: extracción, control de hash, staging y upsert atómico."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando proceso ETL...")

        datos_crudos_ejemplo = [
            {
                "titulo": "Curso Avanzado de Django",
                "contenido": "Optimización, ORM avanzado y seguridad en Django.",
                "provincia": "Madrid",
                "campo_estudio": "Tecnología",
                "colectivo": "General",
                "url": "https://example.com/django"
            }
        ]

        # Fase 1: Ingesta a Staging
        for item in datos_crudos_ejemplo:
            try:
                contenido_str = f"{item.get('titulo', '')}{item.get('contenido', '')}"
                hash_val = hashlib.sha256(contenido_str.encode('utf-8')).hexdigest()
                
                StagingCursos.objects.get_or_create(
                    hash_contenido=hash_val,
                    defaults={
                        'titulo_raw': item.get('titulo', ''),
                        'contenido_raw': item.get('contenido', ''),
                        'provincia_raw': item.get('provincia', ''),
                        'campo_estudio_raw': item.get('campo_estudio', ''),
                        'colectivo_raw': item.get('colectivo', ''),
                        'url_origen': item.get('url', ''),
                        'estado': 'pendiente'
                    }
                )
            except Exception as e:
                logger.error(f"Error insertando en staging: {e}")

        # Fase 2: Normalización y Upsert a Producción
        pendientes = StagingCursos.objects.filter(estado='pendiente')
        contador = 0

        for item in pendientes:
            try:
                with transaction.atomic():
                    BaseConocimiento.objects.update_or_create(
                        titulo=item.titulo_raw,
                        defaults={
                            'contenido': item.contenido_raw or '',
                            'provincia': item.provincia_raw or '',
                            'campo_estudio': item.campo_estudio_raw or '',
                            'colectivo': item.colectivo_raw or '',
                            'url_oficial': item.url_origen or '',
                            'activo': True
                        }
                    )
                    item.estado = 'validado'
                    item.save()
                    contador += 1
            except DatabaseError as e:
                logger.error(f"Error de base de datos en registro ID {item.id}: {e}")
                item.estado = 'rechazado'
                item.save()

        self.stdout.write(self.style.SUCCESS(f"ETL finalizado. Registros validados: {contador}."))