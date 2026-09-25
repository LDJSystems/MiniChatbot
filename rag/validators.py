from django.core.exceptions import ValidationError

def validar_chat_request(body: dict) -> tuple:
    pregunta = body.get("pregunta")
    if not pregunta or not isinstance(pregunta, str):
        raise ValidationError("El campo 'pregunta' es obligatorio y debe ser un texto.")
    
    filtros = body.get("filtros", {})
    if not isinstance(filtros, dict):
        raise ValidationError("El campo 'filtros' debe ser un diccionario.")
        
    return pregunta.strip(), filtros