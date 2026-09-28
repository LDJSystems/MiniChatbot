from django.db import models


class ConsultaFallida(models.Model):
    motivo_fallo = models.TextField()

    procesado = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Consulta fallida"
        verbose_name_plural = "Consultas fallidas"

    def __str__(self):
        return f"Consulta fallida #{self.id}"


class ContadorDemanda(models.Model):
    base_conocimiento_id = models.IntegerField()

    demanda = models.PositiveIntegerField(default=0)

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-demanda"]
        verbose_name = "Contador de demanda"
        verbose_name_plural = "Contadores de demanda"
        indexes = [
            models.Index(
                fields=["-demanda"],
                name="telemetry_demanda_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Base de conocimiento "
            f"{self.base_conocimiento_id}: {self.demanda}"
        )