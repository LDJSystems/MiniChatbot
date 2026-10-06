import requests
from conocimiento.retriever import recuperar_cursos

def contexto_para_ia(pregunta, filtros=None, max_cursos=5):
    cursos = recuperar_cursos(pregunta, filtros)

    # Deduplicar por contenido (hay cursos repetidos con distinto id)
    vistos, unicos = set(), []
    for c in cursos:
        clave = c.contenido.strip()
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(c)

    bloques = [
        f"[Curso {i}] Provincia: {c.provincia or 'N/D'} | Localidad: {c.localidad or 'N/D'}\n{c.contenido}"
        for i, c in enumerate(unicos[:max_cursos], 1)
    ]
    return "\n\n".join(bloques), unicos

def probar(pregunta, filtros=None):
    contexto, cursos = contexto_para_ia(pregunta, filtros)
    print(f"\n>>> {pregunta}  ({len(cursos)} cursos únicos)")
    for c in cursos:
        print(f"   id={c.id} rank={getattr(c, 'rank', '-')} | {c.contenido[:90]}...")
    return contexto

def preguntar_ollama(pregunta, filtros=None, modelo="llama3.2"):  # cambia por tu modelo
    contexto = probar(pregunta, filtros)
    if not contexto:
        print("Sin contexto: aquí tu API escalaría al agente.")
        return
    prompt = (
        "Eres el asistente de CEFYE. Responde usando SOLO el contexto. "
        "Si la respuesta no está, dilo.\n\n"
        f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"
    )
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": modelo, "prompt": prompt, "stream": False},
        timeout=120,
    )
    print("\n--- RESPUESTA ---\n", r.json()["response"])