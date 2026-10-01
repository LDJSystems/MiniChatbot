# conocimiento/services.py
import re
import logging
import operator
from functools import reduce
from django.db import transaction
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento, StagingCursos

logger = logging.getLogger(__name__)


# ── Servicio de consulta para el chatbot ─────────────────────────────────────

class ChatbotKnowledgeService:
    @staticmethod
    def recuperar_contexto(pregunta: str, limite: int = 3) -> str:
        terminos = [w for w in re.findall(r'\w+', pregunta) if len(w) > 2]

        if not terminos:
            return ""

        query = reduce(operator.and_, (SearchQuery(t, config='spanish') for t in terminos))
        resultados = (
            BaseConocimiento.objects
            .filter(vector_busqueda=query, activo=True)
            .annotate(rank=SearchRank('vector_busqueda', query))
            .order_by('-rank')[:limite]
        )
        return "\n\n".join(r.contenido for r in resultados)


# ── Servicio de promoción staging → BaseConocimiento ─────────────────────────

def promover_staging(queryset=None) -> dict:
    """
    Único punto de entrada para promover registros de StagingCursos a BaseConocimiento.

    Args:
        queryset: QS de StagingCursos a procesar. Si es None, toma todos los 'pendiente'.

    Returns:
        dict con claves 'procesados', 'errores', 'ids_error'
    """
    if queryset is None:
        queryset = StagingCursos.objects.filter(estado='pendiente')

    procesados = 0
    errores = 0
    ids_error = []

    for curso in queryset:
        try:
            with transaction.atomic():
                BaseConocimiento.objects.update_or_create(
                    url_oficial=curso.url_origen,
                    defaults={
                        'titulo':        curso.titulo_raw,
                        'contenido':     curso.contenido_raw or '',
                        'provincia':     curso.provincia_raw or 'N/D',
                        'localidad':     curso.localidad or '',
                        'campo_estudio': curso.campo_estudio_raw or 'N/D',
                        'colectivo':     curso.colectivo_raw or 'N/D',
                        'activo':        True,
                    }
                )
                curso.estado = 'procesado'
                curso.save(update_fields=['estado'])
                procesados += 1

        except Exception:
            logger.exception("Error al promover StagingCursos id=%s", curso.pk)
            curso.estado = 'error'
            curso.save(update_fields=['estado'])
            errores += 1
            ids_error.append(curso.pk)

    return {'procesados': procesados, 'errores': errores, 'ids_error': ids_error}