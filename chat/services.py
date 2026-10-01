from chat.models import Sesion, Mensaje

class ChatSessionService:
    @staticmethod
    def obtener_o_crear_sesion(uuid_str=None, filtros=None):
        if uuid_str:
            try:
                return Sesion.objects.get(uuid=uuid_str)
            except Sesion.DoesNotExist:
                pass
        
        filtros = filtros or {}
        return Sesion.objects.create(
            provincia=filtros.get('provincia'),
            campo_estudio=filtros.get('campo_estudio'),
            colectivo=filtros.get('colectivo')
        )

    @staticmethod
    def guardar_intercambio(sesion, pregunta, respuesta_ia):
        Mensaje.objects.create(
            sesion=sesion,
            rol='user',
            contenido=pregunta,
            fallback_activado=False
        )
        Mensaje.objects.create(
            sesion=sesion,
            rol='bot',
            contenido=respuesta_ia.get('texto_respuesta', ''),
            fallback_activado=respuesta_ia.get('fallback_activado', False)
        )