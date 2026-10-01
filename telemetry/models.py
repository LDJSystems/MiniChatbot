from django.db import models

class ConsultaFallida(models.Model):
    texto_consulta = models.TextField()
    motivo_fallo = models.CharField(max_length=50) # 'sin_resultados', 'timeout', 'error_llm'
    procesado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Consulta fallida"
        verbose_name_plural = "Consultas fallidas"

    def __str__(self):
        return f"Consulta fallida #{self.id}"

class ContadorDemanda(models.Model):
    base_conocimiento_id = models.PositiveIntegerField()

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
            models.Index(
                fields=["base_conocimiento_id"],
                name="telemetry_bc_id_idx",
            ),
        ]

    def __str__(self):
        return f"Base de conocimiento {self.base_conocimiento_id}: {self.demanda}"