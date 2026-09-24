# MiniChatbot — Asesor Virtual CEFYE

Chatbot de asesoramiento formativo para CEFYE. Backend Django con pipeline RAG híbrido sobre PostgreSQL y generación de respuestas mediante Ollama (Llama 3.2) en local. Widget Vanilla JS desplegable como un único `<script>`.

---

## Estructura del proyecto

```
MiniChatbot/
├── chat/           # Sesiones, mensajes y leads (Dev B)
├── conocimiento/   # Base de conocimiento, FTS e ingesta (Dev A)
├── operaciones/    # Telemetría, analítica y mejora continua (Dev B)
├── config/         # Configuración global de Django
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── init-ollama.sh
├── manage.py
├── requirements.txt
└── setup.md
```

### Apps y propietario

| App | Propietario | Responsabilidad principal |
|---|---|---|
| `conocimiento` | Dev A | `BaseConocimiento`, trigger GIN/FTS, ingesta JSON/CSV, pipeline RAG, endpoint `ask/` |
| `chat` | Dev B | `Sesion`, `Mensaje`, `Lead`, endpoints `ask/` (delegado) y `lead/`, widget Vanilla JS |
| `operaciones` | Dev B | `ConsultaFallida`, `ContadorDemanda`, telemetría y panel de analítica |
| `config` | Ambos (PR conjunta) | `settings.py`, URLs raíz, variables de entorno |

---

## 1. Propósito y estrategia de conversión

- **Objetivo primario (Información):** Actuar como asesor virtual experto que resuelve de forma rápida y natural dudas sobre la oferta formativa, cursos, requisitos y metodologías de CEFYE.
- **Objetivo secundario (Conversión — doble vía):**
  - **Vía directa (autogestión):** Enlace visible al formulario oficial de matriculación.
  - **Vía asistida (captación de leads):** El bot recoge los datos de contacto básicos (nombre, teléfono/email) y avisa al equipo de gestión para que un asesor humano contacte al usuario. Es la vía prevista como más utilizada.
- **Fuera de alcance:** Pagos, datos bancarios o documentos de matrícula dentro del chat.

---

## 2. Personalidad y tono

- **Estilo:** Cercano, empático y profesional — el "Asesor de Confianza".
- **Trato:** Respetuoso, cálido y humano (tuteo, sin emojis). Pensado para inspirar confianza en alumnos que retoman su formación, combinando respaldo institucional con acompañamiento paciente.

---

## 3. Fuentes de información e IA local (Ollama)

- **Coste cero en APIs externas:** Se descartan APIs de pago por token. La generación de lenguaje natural la gestiona un modelo de código abierto servido mediante **Ollama**.
- **Modelo:** Llama 3.2 (cuantizado según los recursos del servidor para minimizar la latencia de respuesta).
- **Ingesta de datos:** La información oficial se carga desde ficheros estructurados (JSON/CSV) gestionados desde el panel de Django Admin. Esto garantiza control total sobre el contenido y evita roturas por cambios en el diseño web de CEFYE.
- **Ingesta futura:** La app `operaciones` incorporará un pipeline ETL asíncrono con Celery para automatizar la actualización desde la web pública de CEFYE una vez el núcleo RAG esté validado.

---

## 4. Motor de respuesta — RAG Híbrido con Ollama

El pipeline sigue dos fases estrictas:

1. **Recuperación (Retriever híbrido):**
   - Pre-filtro categórico opcional sobre `provincia`, `campo_estudio` y `colectivo` para acotar el subconjunto relevante.
   - Sobre ese subconjunto, PostgreSQL aplica FTS con índice GIN y un umbral de ranking (`rank >= 0.12`) para evitar falsos rechazos en consultas cortas o descripciones extensas.

2. **Generación (Generator):**
   - El backend empaqueta los fragmentos validados en un contexto estricto y los envía al demonio local de Ollama.
   - Si el Retriever devuelve cero resultados, la llamada al LLM se aborta y se activa el flujo de fallback.

**Red de seguridad contra alucinaciones:** Ollama no inventa respuestas; trabaja exclusivamente sobre los datos verificados que le llegan. Si ningún fragmento supera el umbral, el sistema deriva al equipo de gestión sin pasar por el modelo.

---

## 5. Frontend — Widget Vanilla JS

- **Ubicación:** Botón flotante fijo en la esquina inferior derecha de la web de CEFYE.
- **Panel:** Desplegable/colapsable con caja de texto libre y selectores opcionales de `provincia`, `campo_estudio` y `colectivo`. Los filtros no bloquean la caja de texto.
- **Stack:** Vanilla JS y CSS nativo. Sin frameworks (React, Vue, Angular) para evitar bloat y conflictos con la página anfitriona.
- **Aislamiento:** IIFE o Shadow DOM para que estilos y eventos no contaminen la página host.
- **Accesibilidad:** `focus trap`, atributos ARIA y navegación completa por teclado.
- **Despliegue:** Un único `<script async>` antes del cierre de `</body>` apuntando a `chatbot.min.js`.

---

## 6. Sesiones, historial y captación de leads

- **Sesión efímera:** El UUID de sesión y el estado de los filtros viven en el `sessionStorage` del navegador. Sobreviven a la navegación entre páginas y se destruyen al cerrar la pestaña.
- **Purga automatizada:** Los mensajes se alojan temporalmente en PostgreSQL. Un cron job borra periódicamente los registros con `ultima_actividad` anterior al umbral configurado, cumpliendo con la minimización de datos del RGPD.
- **Leads desacoplados:** La tabla `Lead` no tiene FK hacia `Sesion`. Cuando una sesión se purga, el lead no sufre borrado en cascada.
- **Integridad de leads:** `CheckConstraints` en base de datos rechazan cualquier inserción sin al menos un contacto válido (email o teléfono) o sin `consentimiento_rgpd = True`.

---

## 7. API y seguridad perimetral

| Endpoint | Método | Responsabilidad |
|---|---|---|
| `/api/chat/ask/` | POST | Recibe payload híbrido, ejecuta Retriever, llama a Ollama, devuelve respuesta con flags |
| `/api/chat/lead/` | POST | Valida e inserta datos de contacto del lead |

- **Rate limiting:** `django-ratelimit` por IP sobre ambos endpoints.
- **CORS:** `django-cors-headers` restringido a los subdominios oficiales de CEFYE. Sin comodines abiertos (`*`).

---

## 8. Esquema de datos para búsqueda

La tabla `BaseConocimiento` separa dos tipos de columnas:

- **Filtros estrictos (B-Tree):** `provincia`, `campo_estudio`, `colectivo`. Descarte mecánico previo a cualquier cálculo de texto.
- **Texto libre (GIN):** `titulo`, `contenido`. Sobre este subconjunto aplica el FTS.

**Trigger PostgreSQL (`tg_bc_actualizar_vector`):** Recalcula automáticamente el campo `vector_busqueda` en cada `INSERT` y `UPDATE` usando `setweight` con pesos A (`titulo`) y B (`contenido`), con el diccionario `pg_catalog.spanish`.

---

## 9. Ranking híbrido y umbral de corte

- **Pre-filtro categórico:** Opcional y flexible. Permite consultas de ámbito nacional o multi-perfil sin descartar registros de forma ciega.
- **Ponderación (`setweight`):**
  - Peso A (1.0) → `titulo`
  - Peso B (0.4) → `contenido`
- **Umbral:** `rank >= 0.12`. Calibrado para evitar falsos rechazos en textos cortos o descripciones largas.
- **Guardián de Ollama:** Si la búsqueda devuelve cero fragmentos válidos, la petición al LLM se aborta y el sistema pasa a estado de fallback.

---

## 10. Telemetría y mejora continua

- **Fallbacks:** Se registran en `ConsultaFallida` (app `operaciones`) las consultas que no superan el Retriever, junto con el texto libre y los filtros aplicados.
- **Éxitos:** Se incrementan contadores agregados en `ContadorDemanda` vinculados al ID del curso y los filtros. Sin almacenar el texto plano de la consulta (minimización RGPD).
- **Ciclo de mejora:** El equipo de CEFYE identifica desde Django Admin qué combinaciones geográficas o de colectivos no tienen cobertura, añade la entrada a `BaseConocimiento` y marca el registro de telemetría como `procesado = True`.

---

## 11. Esquema relacional y aislamiento de dominios

| Dominio | Tablas | Tipo |
|---|---|---|
| Conocimiento | `BaseConocimiento`, `StagingCursos` | Persistente |
| Conversación | `Sesion`, `Mensaje` | Volátil (purgable) |
| Comercial | `Lead` | Persistente |
| Telemetría | `ConsultaFallida`, `ContadorDemanda` | Persistente |

**Regla clave:** No existen FK entre el dominio volátil y los dominios persistentes. La purga de sesiones no arrastra leads ni telemetría.

---

## 12. Contratos de API

### `POST /api/chat/ask/`

**Request:**
```json
{
  "sesion_uuid": "uuid-v4",
  "consulta": "texto libre del usuario",
  "provincia": "Valladolid",
  "campo_estudio": "Administración",
  "colectivo": "desempleados"
}
```
> `provincia`, `campo_estudio` y `colectivo` son opcionales. Si no llegan, la búsqueda omite el pre-filtro categórico.

**Response:**
```json
{
  "texto_respuesta": "texto generado por Ollama",
  "requiere_accion_comercial": false,
  "fallback_activado": false
}
```

### `POST /api/chat/lead/`

**Request:**
```json
{
  "nombre": "string · requerido",
  "email": "string · requerido si no hay telefono",
  "telefono": "string · requerido si no hay email",
  "provincia": "string · requerido",
  "campo_estudio": "string · requerido",
  "colectivo": "string · requerido",
  "consentimiento_rgpd": true,
  "sesion_uuid": "uuid-v4 · opcional"
}
```

**Response éxito:** `{ "ok": true }`

**Response error:** `{ "ok": false, "errores": { "campo": "descripción" } }`

---

## 13. Widget — empaquetado e integración

| Archivo | Contenido |
|---|---|
| `chat/static/chatbot.js` | Código fuente sin minificar · Shadow DOM o IIFE · máquina de estados |
| `chat/static/chatbot.css` | Estilos encapsulados · identidad visual CEFYE |
| `chat/static/chatbot.min.js` | Salida minificada lista para producción |

Integración en producción:
```html
<script async src="https://tudominio.com/static/chatbot.min.js"></script>
</body>
```

---

## 14. Despliegue — Docker Compose

Cuatro servicios:

| Servicio | Imagen | Notas |
|---|---|---|
| `db` | PostgreSQL 17 | Red interna · puerto 5432 no expuesto al exterior · volumen `pg_data` |
| `ollama` | ollama/ollama | Red interna · puerto 11434 no expuesto · volumen `ollama_models` para cachear pesos de Llama 3.2 |
| `web` | Dockerfile local | Django + Gunicorn · orquesta el pipeline RAG |
| `nginx` | nginx:alpine | Único punto público (80/443) · sirve estáticos y hace proxy a `web` |

---

## 15. Stack tecnológico y dependencias

```
Django>=6.1,<7.0
psycopg2-binary
gunicorn
django-environ
django-cors-headers
django-ratelimit
ollama
```

> `django-cors-headers` no está aún en `requirements.txt` — añadirlo antes de implementar el endpoint `ask/`.

**Prohibido:**
- Librerías NLP pesadas (SpaCy, NLTK) — las operaciones vectoriales las gestiona PostgreSQL.
- Frameworks de scraping en esta fase — la ingesta es JSON/CSV desde Django Admin.
- `pip freeze` para generar `requirements.txt` — solo dependencias top-level.

---

## 16. Ingesta de datos

### Fase actual — JSON/CSV manual

La información oficial de CEFYE se carga desde ficheros estructurados mediante un comando de gestión Django:

```bash
python manage.py cargar_conocimiento --fichero dataset_cefye.json
```

El comando normaliza las variables categóricas al vocabulario controlado e inserta en `BaseConocimiento`. El trigger de PostgreSQL recalcula el vector GIN automáticamente.

### Fase futura — ETL asíncrono (app `operaciones`)

Una vez validado el núcleo RAG, la app `operaciones` incorporará:

- **Celery Beat:** Tareas programadas en horarios de baja concurrencia.
- **Tabla de staging (`StagingCursos`):** Buffer intermedio con `hash_contenido` para deduplicación.
- **Upsert atómico:** Vuelco a `BaseConocimiento` con recálculo automático del índice GIN.