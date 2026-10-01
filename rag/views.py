import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from django.db.models import F
from django.db import IntegrityError
from telemetry.models import ConsultaFallida, ContadorDemanda
from rag.retriever import recuperar_cursos
from rag.generator import generar_respuesta_ia
from chat.services import ChatSessionService

logger = logging.getLogger(__name__)

@api_view(['POST'])
@ratelimit(key='ip', rate='5/m', block=False)
def chat_ask_view(request):
    if getattr(request, 'limited', False):
        return Response(
            {"error": "Demasiadas solicitudes. Has superado el límite de 5 peticiones por minuto."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    data_payload = request.data
    pregunta = data_payload.get('pregunta', '').strip()
    sesion_uuid = data_payload.get('sesion_uuid')
    filtros = data_payload.get('filtros', {})

    if not pregunta:
        return Response({"error": "La consulta no puede estar vacía"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Gestionar sesión
        sesion = ChatSessionService.obtener_o_crear_sesion(sesion_uuid, filtros)

        # 2. Recuperación de contexto
        resultados = recuperar_cursos(pregunta, filtros)
        
        # --- CORTOCIRCUITO LÓGICO ---
        if not resultados:
            logger.info(f"[Escalado] Cero resultados para: '{pregunta}'. Derivando a agente.")
            
            # Registrar en telemetría el fallo de búsqueda
            _registrar_fallo(pregunta, 'sin_resultados')
            
            # Preparar payload de derivación
            resultado_escalado = {
                "texto_respuesta": "No he encontrado formación exacta para tu consulta en este momento. ¿Deseas que un orientador de nuestro equipo contacte contigo para analizar tu caso en detalle?",
                "requiere_accion": "ESCALADO_AGENTE",
                "contexto_busqueda": pregunta
            }
            
            # Guardar en el historial de la sesión
            ChatSessionService.guardar_intercambio(sesion, pregunta, resultado_escalado)
            
            # Finalizar petición sin despertar al LLM
            return Response({
                "sesion_uuid": str(sesion.uuid),
                **resultado_escalado
            }, status=status.HTTP_200_OK)
        # -----------------------------

        # Protección contra desbordamiento: acotamos el bloque principal para el LLM
        resultados_para_ia = resultados
        es_listado_masivo = len(resultados) > 10
        if es_listado_masivo:
            resultados_para_ia = resultados[:10]

        # 3. Generación LLM (El LLM solo se ejecuta si hay cursos reales)
        resultado_ia = generar_respuesta_ia(pregunta, resultados_para_ia)

        if es_listado_masivo and "texto_respuesta" in resultado_ia:
            resultado_ia["texto_respuesta"] += f"\n\n*(Mostrando los primeros 10 resultados de un total de {len(resultados)} encontrados en la provincia).* "

        # 4. Persistencia del intercambio
        ChatSessionService.guardar_intercambio(sesion, pregunta, resultado_ia)

        # 5. Registro de Telemetría (Demanda)
        _registrar_demanda(resultados_para_ia)

        respuesta_final = {
            "sesion_uuid": str(sesion.uuid),
            **resultado_ia
        }

        return Response(respuesta_final, status=status.HTTP_200_OK)

    except TimeoutError:
        _registrar_fallo(pregunta, 'timeout')
        return Response({"error": "El servicio de IA está saturado."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
    except Exception as e:
        logger.error(f"Error procesando la consulta: {str(e)}")
        _registrar_fallo(pregunta, 'error_llm')
        return Response({"error": "Error interno procesando la consulta."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

def _registrar_fallo(query: str, motivo: str):
    """Guarda silenciosamente el fallo sin tumbar la respuesta HTTP."""
    try:
        ConsultaFallida.objects.create(texto_consulta=query, motivo_fallo=motivo)
    except Exception as e:
        logger.error(f"Fallo de BD al guardar ConsultaFallida: {e}")

def _registrar_demanda(resultados):
    """Incremento atómico de demanda tolerante a condiciones de carrera."""
    try:
        for r in resultados:
            curso_id = getattr(r, 'id', None)
            provincia = getattr(r, 'provincia', 'N/D')
            
            if not curso_id:
                continue
                
            updated = ContadorDemanda.objects.filter(
                base_conocimiento_id=curso_id
            ).update(demanda=F('demanda') + 1)
            
            if not updated:
                try:
                    ContadorDemanda.objects.create(
                        base_conocimiento_id=curso_id,
                        provincia=provincia,
                        demanda=1
                    )
                except IntegrityError:
                    ContadorDemanda.objects.filter(
                        base_conocimiento_id=curso_id
                    ).update(demanda=F('demanda') + 1)
    except Exception as e:
        logger.error(f"Fallo de BD al guardar ContadorDemanda: {e}")