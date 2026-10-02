import uuid
from django.db import models
from django.db.models import Q


class Lead(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default="")   
    telefono = models.CharField(max_length=30, blank=True, default="")
    provincia = models.CharField(max_length=100)
    campo_estudio = models.CharField(max_length=150)
    colectivo = models.CharField(max_length=100)
<<<<<<< HEAD
=======

    experiencia_profesional = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    objetivo = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

>>>>>>> 355ff4ccd38a382dde1d0284ee78e5eadf234650
    consentimiento_rgpd = models.BooleanField(default=False)

    sesion_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=True,   
        null=True,
        blank=True,
    )

    procesado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(email__gt="") | Q(telefono__gt=""),
                name="lead_email_o_telefono",
            ),
            models.CheckConstraint(
                condition=Q(consentimiento_rgpd=True),
                name="lead_consentimiento_rgpd",
            ),
            models.CheckConstraint(
                condition=Q(nombre__isnull=False) & ~Q(nombre=""),
                name="lead_nombre_no_vacio",
            ),
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return self.nombre