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
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
    url = f"{base_url.rstrip('/')}/api/generate"
    model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')

    # Safety net: si por algún motivo llega vacío, forzamos un string vacío en el contexto
    contexto_str = "\n\n".join([
        f"- Curso: {_get_attr(r, 'titulo')}\n  Descripción: {_get_attr(r, 'contenido')}\n  Enlace: {_get_attr(r, 'url_oficial', None) or 'N/D'}"
        for r in resultados
    ]) if resultados else "No hay resultados disponibles en la base de datos."

    # Prompt reestructurado (Fase 4.3: Idioma, Tono, Formato y Anti-Alucinación)
    prompt = (
        "Eres el asistente virtual experto en formación y empleo de CEFYE en Castilla y León. "
        "Tu objetivo es recomendar cursos basándote ÚNICAMENTE en el contexto proporcionado.\n\n"
        "REGLAS ESTRICTAS:\n"
        "1. IDIOMA Y TONO: Responde siempre en español. Mantén un tono profesional, empático y directo. Trata al usuario de tú.\n"
        "2. FORMATO: Usa Markdown para estructurar tu respuesta. Usa negritas para los títulos de los cursos y listas con viñetas para que sea fácil de leer.\n"
        "3. NO INVENTES INFORMACIÓN: Basa tu respuesta EXCLUSIVAMENTE en el bloque de CONTEXTO. Si te preguntan algo que no aparece en el contexto, responde exactamente: 'No dispongo de esa información específica en este momento, ¿quieres que un asesor de nuestro equipo se ponga en contacto contigo?'. No inventes fechas, modalidades ni requisitos.\n"
        "4. GEOGRAFÍA: Si un curso indica 'CEFYE-LEON' (o cualquier otra provincia como Burgos, Palencia, Valladolid, Zamora, Salamanca, Segovia, Soria, Ávila), significa que se imparte presencialmente en esa capital.\n\n"
        f"CONTEXTO RECUPERADO:\n{contexto_str}\n\n"
        f"PREGUNTA DEL USUARIO:\n{pregunta}\n\n"
        "RESPUESTA:"
    )

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Temperatura baja para maximizar la adherencia al contexto
            "top_k": 10
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        texto = data.get('response', '').strip()

        if not texto:
            raise ValueError("Ollama devolvió una respuesta vacía.")

        logger.debug(f"[Generator] Respuesta Ollama ({len(texto)} chars generados).")

        return {
            "texto_respuesta": texto,
            "requiere_accion_comercial": False,
            "fallback_activado": False
        }

    except requests.exceptions.Timeout:
        logger.error(f"[Generator] Timeout conectando con Ollama en {url}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[Generator] Error de conexión con Ollama en {url}: {e}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"[Generator] Error HTTP de Ollama: {e}")
    except (ValueError, KeyError) as e:
        logger.error(f"[Generator] Error procesando respuesta de Ollama: {e}")

    # Fallback técnico por caída del LLM
    return {
        "texto_respuesta": "El servicio de inteligencia artificial se encuentra temporalmente saturado o en mantenimiento. Por favor, intenta de nuevo en unos minutos.",
        "requiere_accion_comercial": True,
        "fallback_activado": True
    }