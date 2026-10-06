import logging
from celery import shared_task
from django.db.models import F
from django.db import IntegrityError
from django.db import transaction

from chat.services import ChatSessionService
from rag.retriever import recuperar_cursos
from rag.generator import generar_respuesta_ia
from telemetry.models import ConsultaFallida, ContadorDemanda

logger = logging.getLogger(__name__)

def _registrar_fallo(query: str, motivo: str):
    with transaction.atomic():
        ConsultaFallida.objects.create(texto_consulta=query, motivo_fallo=motivo)
        
def _registrar_demanda(resultados):
    try:
        for r in resultados:
            curso_id = getattr(r, 'id', None)
            provincia = getattr(r, 'provincia', 'N/D')
            if not curso_id: continue
            
            updated = ContadorDemanda.objects.filter(base_conocimiento_id=curso_id).update(demanda=F('demanda') + 1)
            if not updated:
                try:
                    ContadorDemanda.objects.create(base_conocimiento_id=curso_id, provincia=provincia, demanda=1)
                except IntegrityError:
                    ContadorDemanda.objects.filter(base_conocimiento_id=curso_id).update(demanda=F('demanda') + 1)
    except Exception as e:
        logger.error(f"Fallo de BD al guardar ContadorDemanda: {e}")

@shared_task(bind=True, max_retries=2, time_limit=120)
def procesar_chat_ia_task(self, pregunta, filtros, sesion_uuid):
    try:
        sesion = ChatSessionService.obtener_o_crear_sesion(sesion_uuid, filtros)
        resultados = recuperar_cursos(pregunta, filtros)
        
        if not resultados:
            logger.info(f"[Escalado] Cero resultados para: '{pregunta}'. Derivando a agente.")
            _registrar_fallo(pregunta, 'sin_resultados')
            respuesta_escalada = {
                "texto_respuesta": "No he encontrado formación exacta para tu consulta en este momento. ¿Deseas que un orientador contacte contigo?",
                "requiere_accion": "ESCALADO_AGENTE",
                "contexto_busqueda": pregunta
            }
            ChatSessionService.guardar_intercambio(sesion, pregunta, respuesta_escalada)
            return {"sesion_uuid": str(sesion.uuid), **respuesta_escalada}

        es_listado_masivo = len(resultados) > 10
        resultados_para_ia = resultados[:10] if es_listado_masivo else resultados

        # Aislamiento de la llamada al LLM mediante un savepoint transaccional
        try:
            with transaction.atomic():
                resultado_ia = generar_respuesta_ia(pregunta, resultados_para_ia)
        except Exception as llm_exc:
            _registrar_fallo(pregunta, 'error_llm')
            raise llm_exc

        if es_listado_masivo and "texto_respuesta" in resultado_ia:
            resultado_ia["texto_respuesta"] += f"\n\n*(Mostrando 10 de {len(resultados)} resultados encontrados).* "

        ChatSessionService.guardar_intercambio(sesion, pregunta, resultado_ia)
        _registrar_demanda(resultados_para_ia)

        return {"sesion_uuid": str(sesion.uuid), **resultado_ia}
        
    except Exception as e:
        logger.error(f"Fallo en worker de Celery para '{pregunta}': {str(e)}")
        raise e