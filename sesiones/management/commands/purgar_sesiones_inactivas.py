from datetime import timedelta

import environ
from django.core.management.base import BaseCommand
from django.utils import timezone

from sesiones.models import Sesion

env = environ.Env()


class Command(BaseCommand):
    help = "Purga sesiones inactivas (borrando sus Mensajes vía FK CASCADE)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No borra, solo muestra cuántas sesiones serían eliminadas.",
        )

    def handle(self, *args, **options):
        inactivity_seconds = env.int("SESIONES_INACTIVAS_UMBRAL_SECONDS", default=3600)
        threshold = timezone.now() - timedelta(seconds=inactivity_seconds)

        qs = Sesion.objects.filter(ultima_actividad__lt=threshold)

        if options["dry_run"]:
            self.stdout.write(f"[dry-run] Sesiones a eliminar: {qs.count()}")
            return

        deleted_count, _ = qs.delete()  # delete() devuelve (num_obj_deleted, dict_por_model)
        self.stdout.write(
            self.style.SUCCESS(
                f"Purga completada. Sesiones eliminadas (aprox): {deleted_count}. Umbral: {threshold}."
            )
        )
