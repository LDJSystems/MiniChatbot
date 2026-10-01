from django.core.management.base import BaseCommand
from conocimiento.services import promover_staging


class Command(BaseCommand):
    help = 'Procesa los cursos pendientes de staging y los consolida en BaseConocimiento.'

    def handle(self, *args, **options):
        resultado = promover_staging()

        if resultado['errores']:
            self.stdout.write(
                self.style.WARNING(f"IDs con error: {resultado['ids_error']}")
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Finalizado. Procesados: {resultado['procesados']}, "
                f"Errores: {resultado['errores']}"
            )
        )