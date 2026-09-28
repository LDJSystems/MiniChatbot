from rest_framework import serializers
from .models import Lead, Provincia

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['nombre', 'email', 'telefono', 'provincia', 'campo_estudio', 'colectivo', 'consentimiento_rgpd']

    def validate_provincia(self, value):
        provincia_limpia = value.strip()
        if not Provincia.objects.filter(nombre__iexact=provincia_limpia).exists():
            raise serializers.ValidationError("La provincia indicada no pertenece a Castilla y León.")
        return provincia_limpia

    def validate(self, data):
        if not data.get('consentimiento_rgpd'):
            raise serializers.ValidationError({"consentimiento_rgpd": "El consentimiento RGPD es obligatorio."})
        if not data.get('email') and not data.get('telefono'):
            raise serializers.ValidationError("Debe proporcionar al menos un correo electrónico o un teléfono de contacto.")
        return data