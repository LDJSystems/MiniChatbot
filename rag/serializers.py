# rag/serializers.py
from django.core.exceptions import ValidationError

class ChatRequestValidator:
    @staticmethod
    def validar(data: dict) -> tuple[str, dict]:
        pregunta = data.get('pregunta', '').strip()
        if not pregunta:
            raise ValidationError("El campo 'pregunta' es obligatorio y no puede estar vacío.")
        
        filtros = data.get('filtros', {})
        if not isinstance(filtros, dict):
            raise ValidationError("El campo 'filtros' debe ser un diccionario.")
            
        return pregunta, filtros