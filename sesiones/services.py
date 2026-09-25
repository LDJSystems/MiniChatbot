
from uuid import UUID
from django.utils import timezone
from .models import Sesion

def crear_o_recuperar_sesion(session_id: UUID) -> Sesion:
    sesion, creada = Sesion.objects.get_or_create(id=session_id)

    if not creada:
        Sesion.objects.filter(id=session_id).update(ultima_actividad=timezone.now())

    # Devuelves la instancia
    return Sesion.objects.get(id=session_id)

"""Nota: hago un get al final para devolver una instancia consistente (si no importa la instancia actualizada en memoria, podrías devolver sesion directamente)."""