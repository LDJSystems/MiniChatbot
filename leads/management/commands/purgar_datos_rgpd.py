from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from leads.models import Lead
from telemetry.models import ConsultaFallida

class Command(BaseCommand):
    help = "Purga datos obsoletos según la política de retención RGPD."

    def handle(self, *args, **options):
        # 1. Retención de ConsultaFallida: 90 días
        limite_consultas = timezone.now() - timedelta(days=90)
        eliminadas_consultas, _ = ConsultaFallida.objects.filter(creado_en__lt=limite_consultas).delete()
        self.stdout.write(self.style.SUCCESS(f"Purgadas {eliminadas_consultas} consultas fallidas antiguas."))

        # 2. Retención de Leads no procesados/inactivos: 365 días
        limite_leads = timezone.now() - timedelta(days=365)
        eliminados_leads, _ = Lead.objects.filter(procesado=False, creado_en__lt=limite_leads).delete()
        self.stdout.write(self.style.SUCCESS(f"Purgados {eliminados_leads} leads inactivos antiguos."))