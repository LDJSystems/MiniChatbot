# rag/serializers.py
from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    pregunta = serializers.CharField(
        max_length=1000,
        required=True,
        allow_blank=False,
        error_messages={
            'required': "El campo 'pregunta' es obligatorio.",
            'blank':    "El campo 'pregunta' no puede estar vacío.",
            'max_length': "La pregunta supera el límite máximo de 1000 caracteres.",
        }
    )

    provincia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    colectivo = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    # sesion_uuid: opcional para mantener compatibilidad con clientes anteriores.
    # Cuando no se envía, el contexto conversacional no está disponible.
    sesion_uuid = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        """
        Construye el diccionario 'filtros' que espera el retriever
        a partir de los campos planos, descartando los vacíos.
        """
        filtros = {}
        for key in ('provincia', 'colectivo'):
            valor = attrs.get(key, '')
            if valor:
                filtros[key] = valor.strip()

        attrs['filtros'] = filtros
        return attrs