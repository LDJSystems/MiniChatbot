from django.db import models

class ConsultaFallida(models.Model):
    texto_consulta = models.TextField()
    motivo_fallo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fallo: {self.texto_consulta[:50]}"
