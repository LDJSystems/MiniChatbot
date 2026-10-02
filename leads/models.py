import uuid

from django.db import models
from django.db.models import Q


class Lead(models.Model):
    nombre = models.CharField(max_length=150)

    email = models.EmailField(blank=True, null=True)

    telefono = models.CharField(max_length=30, blank=True, null=True)

    provincia = models.CharField(max_length=100)

    campo_estudio = models.CharField(max_length=150)

    colectivo = models.CharField(max_length=100)

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

    consentimiento_rgpd = models.BooleanField(default=False)

    sesion_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,
        blank=True,
    )

    procesado = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(telefono__isnull=False),
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