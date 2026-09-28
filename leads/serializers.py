from rest_framework import serializers

from .models import Lead


class LeadSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lead
        fields = [
            "id",
            "nombre",
            "email",
            "telefono",
            "provincia",
            "campo_estudio",
            "colectivo",
            "consentimiento_rgpd",
            "sesion_uuid",
            "procesado",
            "creado_en",
        ]

        read_only_fields = [
            "id",
            "procesado",
            "creado_en",
        ]

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip()
        telefono = (attrs.get("telefono") or "").strip()

        if not email and not telefono:
            raise serializers.ValidationError(
                "Debe proporcionar email o teléfono."
            )

        if not attrs.get("consentimiento_rgpd"):
            raise serializers.ValidationError(
                "Es necesario aceptar el consentimiento RGPD."
            )

        attrs["email"] = email
        attrs["telefono"] = telefono

        return attrs