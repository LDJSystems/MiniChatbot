from leads.serializers import LeadSerializer
from leads.models import Lead

def exportar_datos_usuario(email: str) -> dict:
    """Derecho a la portabilidad: exporta toda la información asociada a un email."""
    leads = Lead.objects.filter(email=email)
    if not leads.exists():
        return {"error": "No se encontraron registros para este correo."}
    
    serializer = LeadSerializer(leads, many=True)
    return {
        "email_consultado": email,
        "total_registros": leads.count(),
        "datos": serializer.data
    }

def borrar_datos_usuario(email: str) -> int:
    """Derecho al olvido: elimina físicamente o anonimiza los registros del usuario."""
    leads_qs = Lead.objects.filter(email=email)
    cantidad, _ = leads_qs.delete()
    return cantidad