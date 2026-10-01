# rag/generator.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def _get_attr(obj, name, default="N/D"):
    """Permite leer tanto diccionarios como objetos ORM de forma segura."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def generar_respuesta_ia(pregunta: str, resultados: list) -> dict:
    # Cambiado por defecto a localhost para ejecución nativa en Windows
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
    url = f"{base_url.rstrip('/')}/api/generate"
    model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')

    if not resultados:
        # En lugar de responder directamente, pedimos al LLM que responda
        # de forma honesta indicando que no tiene contexto específico
        contexto_str = (
            "No se han encontrado cursos o formaciones específicas en la base de datos "
            "que coincidan con la consulta del usuario."
        )
        fallback = True
    else:
        contexto_str = "\n\n".join([
            f"- Título: {_get_attr(r, 'titulo')}\n  Contenido: {_get_attr(r, 'contenido')}\n  URL: {_get_attr(r, 'url_oficial', None) or 'N/D'}"
            for r in resultados
        ])
        fallback = False

    # Prompt blindado contra Prompt Injection
    prompt = (
    "Eres un asistente especializado en formación y empleo de Castilla y León. "
    "Ten en cuenta estas equivalencias de nombres en la base de datos: "
    "'CEFYE-LEON' o 'CEFYE León' equivale a cursos impartidos en León capital. "
    "'CEFYE-BURGOS' o 'CEFYE Burgos' equivale a cursos impartidos en Burgos capital. "
    "'CEFYE-PALENCIA' o 'CEFYE Palencia' equivale a cursos impartidos en Palencia capital. "
    "'CEFYE-VALLADOLID' o 'CEFYE Valladolid' equivale a cursos impartidos en Valladolid capital. "
    "'CEFYE-ZAMORA' o 'CEFYE Zamora' equivale a cursos impartidos en Zamora capital. "
    "'CEFYE-SALAMANCA' o 'CEFYE Salamanca' equivale a cursos impartidos en Salamanca capital. "
    "'CEFYE-SEGOVIA' o 'CEFYE Segovia' equivale a cursos impartidos en Segovia capital. "
    "'CEFYE-SORIA' o 'CEFYE Soria' equivale a cursos impartidos en Soria capital. "
    "'CEFYE-AVILA' o 'CEFYE Ávila' equivale a cursos impartidos en Ávila capital. "
    "Usa exclusivamente el siguiente contexto para responder a la pregunta. "
    "Si el contexto no contiene información relevante, indícalo amablemente y sugiere "
    "al usuario que reformule su consulta o contacte con el servicio de orientación.\n\n"
    f"CONTEXTO:\n{contexto_str}\n\n"
    f"PREGUNTA: {pregunta}\n\n"
    "RESPUESTA DIRECTA:"
)

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }

    try:
        # Timeout ampliado a 90s para evitar saturación en consultas masivas
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        texto = data.get('response', '').strip()

        if not texto:
            raise ValueError("Ollama devolvió una respuesta vacía.")

        logger.debug(f"[Generator] Respuesta Ollama ({len(texto)} chars), fallback={fallback}")

        return {
            "texto_respuesta": texto,
            "requiere_accion_comercial": fallback,
            "fallback_activado": fallback
        }

    except requests.exceptions.Timeout:
        logger.error(f"[Generator] Timeout conectando con Ollama en {url}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[Generator] Error de conexión con Ollama en {url}: {e}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"[Generator] Error HTTP de Ollama: {e}")
    except (ValueError, KeyError) as e:
        logger.error(f"[Generator] Error procesando respuesta de Ollama: {e}")

    return {
        "texto_respuesta": "El servicio de IA se encuentra temporalmente saturado. Por favor, intenta más tarde.",
        "requiere_accion_comercial": True,
        "fallback_activado": True
    }