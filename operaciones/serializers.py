from rest_framework import serializers
from .models import Lead, Provincia, Localidad

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['nombre', 'email', 'telefono', 'provincia', 'localidad', 'campo_estudio', 'colectivo', 'consentimiento_rgpd']

    def validate_provincia(self, value):
        provincia_limpia = value.strip()
        if not Provincia.objects.filter(nombre__iexact=provincia_limpia).exists():
            raise serializers.ValidationError("La provincia indicada no pertenece a Castilla y León.")
        return provincia_limpia

    def validate(self, data):
        provincia_nombre = data.get('provincia')
        localidad_nombre = data.get('localidad')

        if localidad_nombre and provincia_nombre:
            provincia_limpia = provincia_nombre.strip()
            localidad_limpia = localidad_nombre.strip()
            if not Localidad.objects.filter(
                nombre__iexact=localidad_limpia,
                provincia__nombre__iexact=provincia_limpia
            ).exists():
                raise serializers.ValidationError({"localidad": "La localidad indicada no pertenece a la provincia seleccionada."})

        if not data.get('consentimiento_rgpd'):
            raise serializers.ValidationError({"consentimiento_rgpd": "El consentimiento RGPD es obligatorio."})
        if not data.get('email') and not data.get('telefono'):
            raise serializers.ValidationError("Debe proporcionar al menos un correo electrónico o un teléfono de contacto.")
        return data