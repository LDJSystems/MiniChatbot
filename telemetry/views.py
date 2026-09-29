from django.shortcuts import render

from .models import ContadorDemanda


def tendencias_demanda(request):
    tendencias = (
        ContadorDemanda.objects
        .order_by("-demanda")[:20]
    )

    context = {
        "tendencias": tendencias,
    }

    return render(
        request,
        "telemetry/tendencias.html",
        context,
    )