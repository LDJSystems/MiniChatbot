from .models import ConsultaFallida, ContadorDemanda


def registrar_fallo(motivo):
    ConsultaFallida.objects.create(
        motivo_fallo=motivo
    )


def incrementar_demanda(base_conocimiento_id):
    contador, _ = ContadorDemanda.objects.get_or_create(
        base_conocimiento_id=base_conocimiento_id
    )

    contador.demanda += 1
    contador.save(
        update_fields=[
            "demanda",
            "actualizado_en",
        ]
    )
