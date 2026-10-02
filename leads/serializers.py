<<<<<<< HEAD
import unicodedata
=======

>>>>>>> 355ff4ccd38a382dde1d0284ee78e5eadf234650
from rest_framework import serializers
from .models import Lead
from .validators import PROVINCIAS_CYL


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower().strip()


class LeadSerializer(serializers.ModelSerializer):

    sesion_uuid = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Lead
        fields = [
<<<<<<< HEAD
            "id", "nombre", "email", "telefono", "provincia",
            "campo_estudio", "colectivo", "consentimiento_rgpd",
            "sesion_uuid", "procesado", "creado_en",
=======
            "id",
            "nombre",
            "email",
            "telefono",
            "provincia",
            "campo_estudio",
            "colectivo",
            "experiencia_profesional",
            "objetivo",
            "consentimiento_rgpd",
            "sesion_uuid",
            "procesado",
            "creado_en",
>>>>>>> 355ff4ccd38a382dde1d0284ee78e5eadf234650
        ]
        read_only_fields = ["id", "procesado", "creado_en"]

    def validate_provincia(self, value):
        valor_norm = _normalizar(value)
        provincias_norm = {_normalizar(p): p for p in PROVINCIAS_CYL}
        if valor_norm not in provincias_norm:
            raise serializers.ValidationError(
                f"'{value}' no es una provincia de Castilla y León. "
                f"Provincias válidas: {', '.join(PROVINCIAS_CYL)}."
            )
        return provincias_norm[valor_norm]

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip()
        telefono = (attrs.get("telefono") or "").strip()

        if not email and not telefono:
            raise serializers.ValidationError("Debe proporcionar email o teléfono.")

        if not attrs.get("consentimiento_rgpd"):
            raise serializers.ValidationError("Es necesario aceptar el consentimiento RGPD.")

        attrs["email"] = email
        attrs["telefono"] = telefono
<<<<<<< HEAD
        return attrs
=======

        return attrs

>>>>>>> 355ff4ccd38a382dde1d0284ee78e5eadf234650
