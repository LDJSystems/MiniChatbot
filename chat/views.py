"""
chat/views.py — Endpoint principal del Chatbot CEFYE
Orquesta: Sesión → RAG (BaseConocimiento) → Ollama → Respuesta

Ajustado a los modelos reales:
  - chat.models:        Sesion, Mensaje (rol: 'user'|'bot', campo creado_en)
  - conocimiento.models: BaseConocimiento (vector_busqueda, activo, colectivo…)
"""

import json
import logging
import os

import requests
from django.db import models
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from chat.models import Sesion, Mensaje
from conocimiento.models import BaseConocimiento

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Configuración (desde .env vía variables de entorno)
# ──────────────────────────────────────────────────────────────────
OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.01"))
RAG_MAX_CURSOS = int(os.getenv("RAG_MAX_CURSOS", "10"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))

SYSTEM_PROMPT = (
    "Eres Alex, el asistente virtual de CEFYE, un centro de formación profesional. "
    "Tu tono es cercano, empático y profesional. Tratas al usuario de tú. No usas emojis. "
    "Responde ÚNICAMENTE con la información de los cursos que se te proporcionan. "
    "Debes listar TODOS los cursos proporcionados en el contexto sin omitir ninguno ni inventar notas sobre límites de resultados."
)

MSG_FALLBACK = (
    "Lo siento, no he encontrado información suficientemente relevante "
    "en nuestra base de conocimiento para responder a tu consulta. "
    "¿Quieres que un asesor de CEFYE se ponga en contacto contigo?"
)

MSG_OLLAMA_KO = (
    "El servicio de IA se encuentra temporalmente saturado. "
    "Por favor, intenta más tarde."
)

MAPA_LOCALIDADES_CYL = {
    "Ávila": ["Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda", "El Barco de Ávila", "Las Navas del Marqués"],
    "Burgos": ["Burgos", "Miranda de Ebro", "Aranda de Duero", "Briviesca", "Medina de Pomar", "Villarcayo de Merindad de Castilla La Vieja"],
    "León": ["León", "Ponferrada", "San Andrés del Rabanedo", "Villaquilambre", "Astorga", "La Bañeza", "Bembibre", "Valencia de Don Juan"],
    "Palencia": ["Palencia", "Aguilar de Campoo", "Guardo", "Venta de Baños", "Villamuriel de Cerrato", "Herrera de Pisuerga"],
    "Salamanca": ["Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes", "Carbajosa de la Sagrada", "Peñaranda de Bracamonte", "Guijuelo"],
    "Segovia": ["Segovia", "Cuéllar", "El Espinar", "Real Sitio de San Ildefonso", "Palazuelos de Eresma", "Nava de la Asunción"],
    "Soria": ["Soria", "Almazán", "El Burgo de Osma-Ciudad de Osma", "Golmayo", "San Esteban de Gormaz", "Ágreda"],
    "Valladolid": ["Valladolid", "Laguna de Duero", "Medina del Campo", "Arroyo de la Encomienda", "Tordesillas", "Cistérniga", "Zaratán", "Simancas"],
    "Zamora": ["Zamora", "Benavente", "Toro", "Morales del Vino", "Puebla de Sanabria", "Villaralbo"]
}


# ──────────────────────────────────────────────────────────────────
# Helpers privados
# ──────────────────────────────────────────────────────────────────

def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    return texto.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')


def _recuperar_cursos(pregunta, provincia="", campo_estudio="", colectivo=""):
    qs = BaseConocimiento.objects.filter(activo=True)
    preg_limpia = _limpiar_texto(pregunta)

    if not provincia:
        for prov, localidades in MAPA_LOCALIDADES_CYL.items():
            if _limpiar_texto(prov) in preg_limpia:
                provincia = prov
                break
            for loc in localidades:
                if _limpiar_texto(loc) in preg_limpia:
                    provincia = prov
                    break

    if provincia:
        localidades_provincia = MAPA_LOCALIDADES_CYL.get(provincia, [])
        qs = qs.filter(
            models.Q(provincia__icontains=provincia) | 
            models.Q(localidad__in=localidades_provincia)
        )
    if campo_estudio:
        qs = qs.filter(campo_estudio__icontains=campo_estudio)
    if colectivo:
        qs = qs.filter(colectivo__icontains=colectivo)

    palabras_listado = ["todos", "listar", "muestrame", "provincia", "listado"]
    es_consulta_amplia = any(k in preg_limpia for k in palabras_listado)

    if es_consulta_amplia or provincia:
        qs = qs.order_by("localidad", "titulo")
    else:
        query = SearchQuery(pregunta, config="spanish")
        qs = (
            qs.filter(vector_busqueda=query)
              .annotate(rank=SearchRank("vector_busqueda", query))
              .filter(rank__gte=RAG_THRESHOLD)
              .order_by("-rank")[:RAG_MAX_CURSOS]
        )

    return list(
        qs.values("titulo", "contenido", "provincia", "localidad",
                  "campo_estudio", "colectivo", "url_oficial")
    ), provincia


def _construir_contexto(cursos):
    """Serializa los cursos recuperados en texto plano para el prompt."""
    bloques = []
    for i, c in enumerate(cursos, 1):
        b = (
            f"[Curso {i}]\n"
            f"Título: {c['titulo']}\n"
            f"Provincia: {c.get('provincia', 'Nacional')}"
        )
        if c.get("localidad"):
            b += f" — {c['localidad']}"
        b += (
            f"\nCampo: {c.get('campo_estudio', '-')}\n"
            f"Destinatarios: {c.get('colectivo', '-')}\n"
            f"Descripción: {c['contenido']}\n"
        )
        if c.get("url_oficial"):
            b += f"Más información: {c['url_oficial']}\n"
        bloques.append(b)
    return "\n".join(bloques)


def _llamar_ollama(contexto, pregunta, historial):
    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nCURSOS DISPONIBLES:\n{contexto}",
        }
    ]
    messages.extend(historial)
    messages.append({"role": "user", "content": pregunta})

    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": 0.0
        }
    }

    resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _historial_sesion(sesion, max_turnos=6):
    msgs = (
        Mensaje.objects.filter(sesion=sesion)
                       .order_by("-creado_en")
                       .values("rol", "contenido")[:max_turnos]
    )
    resultado = []
    for m in reversed(list(msgs)):
        resultado.append({
            "role": "assistant" if m["rol"] == "bot" else "user",
            "content": m["contenido"],
        })
    return resultado


# ──────────────────────────────────────────────────────────────────
# POST /api/chat/ask/
# ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def ask(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    pregunta      = (body.get("pregunta")      or "").strip()
    session_id    = (body.get("session_id")    or "").strip()
    provincia     = (body.get("provincia")     or "").strip()
    campo_estudio = (body.get("campo_estudio") or "").strip()
    colectivo     = (body.get("colectivo")     or "").strip()

    if not pregunta:
        return JsonResponse({"error": "El campo 'pregunta' es obligatorio."}, status=400)

    sesion = None
    if session_id:
        sesion = Sesion.objects.filter(uuid=session_id).first()
    if not sesion:
        sesion = Sesion.objects.create(
            provincia=provincia or None,
            campo_estudio=campo_estudio or None,
            colectivo=colectivo or None,
        )

    Mensaje.objects.create(sesion=sesion, rol="user", contenido=pregunta)

    cursos, provincia_detectada = _recuperar_cursos(pregunta, provincia, campo_estudio, colectivo)
    
    if not cursos:
        Mensaje.objects.create(
            sesion=sesion, rol="bot",
            contenido=MSG_FALLBACK, fallback_activado=True
        )
        return JsonResponse({
            "texto_respuesta":          MSG_FALLBACK,
            "session_id":               str(sesion.uuid),
            "fallback_activado":        True,
            "requiere_accion_comercial": True,
        })

    preg_limpia = _limpiar_texto(pregunta)
    palabras_listado = ["todos", "listar", "muestrame", "provincia", "listado"]
    es_consulta_amplia = any(k in preg_limpia for k in palabras_listado)

    # Cortocircuito absoluto: Si es listado o provincia, omitimos Ollama y devolvemos datos limpios
    if es_consulta_amplia or provincia_detectada:
        localidades_dict = {}
        for c in cursos:
            loc = c.get('localidad') or 'General'
            if loc not in localidades_dict:
                localidades_dict[loc] = []
            localidades_dict[loc].append(c)
        
        prov_nombre = provincia_detectada or provincia or "solicitada"
        lineas = [f"Cursos disponibles en la provincia de {prov_nombre} ({len(cursos)} en total):\n"]
        for loc, lista_c in localidades_dict.items():
            lineas.append(f"**{loc}**")
            for c in lista_c:
                lineas.append(f"- {c['titulo']}")
            lineas.append("")
        
        respuesta = "\n".join(lineas).strip()
    else:
        contexto  = _construir_contexto(cursos)
        historial = _historial_sesion(sesion)
        try:
            respuesta = _llamar_ollama(contexto, pregunta, historial)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            logger.error("[Ollama] Error o timeout: %s", exc)
            return JsonResponse({
                "texto_respuesta": MSG_OLLAMA_KO,
                "session_id": str(sesion.uuid),
                "fallback_activado": True,
                "requiere_accion_comercial": False,
            })

    Mensaje.objects.create(sesion=sesion, rol="bot", contenido=respuesta)

    return JsonResponse({
        "texto_respuesta":          respuesta,
        "session_id":               str(sesion.uuid),
        "fallback_activado":        False,
        "requiere_accion_comercial": False,
    })