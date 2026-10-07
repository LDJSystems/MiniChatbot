from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    # Campo principal — obligatorio
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

    # Filtros geográficos / temáticos — todos opcionales, vienen en el nivel raíz
    provincia     = serializers.CharField(required=False, allow_blank=True, default='')
    campo_estudio = serializers.CharField(required=False, allow_blank=True, default='')
    colectivo     = serializers.CharField(required=False, allow_blank=True, default='')

    # Trazabilidad de sesión — opcional, no se usa en el RAG pero se puede registrar
    sesion_uuid = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        """
        Construye el diccionario 'filtros' que espera el retriever
        a partir de los campos planos, descartando los vacíos.
        """
        filtros = {}
        for key in ('provincia', 'campo_estudio', 'colectivo'):
            valor = attrs.get(key, '').strip()
            if valor:
                filtros[key] = valor

        attrs['filtros'] = filtros
        return attrs