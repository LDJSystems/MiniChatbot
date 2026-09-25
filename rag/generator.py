# rag/generator.py
import requests
from django.conf import settings

class HybridGenerator:
    OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434/api/generate')
    MODEL_NAME = getattr(settings, 'OLLAMA_MODEL', 'llama3')

    @staticmethod
    def generar_respuesta(pregunta: str, resultados: list) -> dict:
        if not resultados:
            return {
                "texto_respuesta": "Lo siento, no he encontrado información suficientemente relevante en nuestra base de conocimiento para responder a tu consulta.",
                "requiere_accion_comercial": True,
                "fallback_activado": True
            }

        contexto_str = "\n\n".join([
            f"- Título: {r.titulo}\n  Contenido: {r.contenido}\n  URL: {r.url_oficial or 'N/D'}"
            for r in resultados
        ])

        prompt = (
            "Eres un asistente técnico especializado. "
            "Responde a la pregunta del usuario basándote exclusivamente en el siguiente contexto:\n\n"
            f"{contexto_str}\n\n"
            f"Pregunta: {pregunta}"
        )

        payload = {
            "model": HybridGenerator.MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(HybridGenerator.OLLAMA_URL, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                texto = data.get('response', 'Sin respuesta del LLM.')
                return {
                    "texto_respuesta": texto,
                    "requiere_accion_comercial": False,
                    "fallback_activado": False
                }
        except requests.RequestException:
            pass

        return {
            "texto_respuesta": "Error de comunicación con el motor de IA. Por favor, intenta más tarde.",
            "requiere_accion_comercial": True,
            "fallback_activado": True
        }