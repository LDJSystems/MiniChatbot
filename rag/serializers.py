from django.core.exceptions import ValidationError
from rest_framework import serializers

class ChatRequestSerializer(serializers.Serializer):
    # DRF valida automáticamente que sea texto, no esté vacío y no exceda la longitud
    pregunta = serializers.CharField(
        max_length=1000, 
        required=True, 
        allow_blank=False,
        error_messages={
            'required': "El campo 'pregunta' es obligatorio.",
            'blank': "El campo 'pregunta' no puede estar vacío.",
            'max_length': "La pregunta supera el límite máximo de 1000 caracteres."
        }
    )
    
    # DictField valida que el body contenga un diccionario {}. Evita el error 500.
    filtros = serializers.DictField(
        required=False, 
        default=dict,
        error_messages={
            'not_a_dict': "El campo 'filtros' debe ser un diccionario válido."
        }
    )

    def validate_filtros(self, value):
        """Valida que los valores dentro del diccionario de filtros sean del tipo correcto."""
        for key, val in value.items():
            if not isinstance(val, (str, int, bool, type(None))):
                raise serializers.ValidationError(
                    f"El valor para el filtro '{key}' tiene un tipo no soportado."
                )
        return value