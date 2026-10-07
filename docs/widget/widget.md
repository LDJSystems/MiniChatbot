# Manual del widget de chatbot (CEFYE)

Guía para el programador que herede, ejecute o integre este widget. Explica **cómo se ejecuta**, **por qué está hecho así** y **qué falta o está desalineado** en el estado actual del código.

---

## 1. Qué es

Un widget de chat embebible en cualquier web: botón flotante abajo a la derecha que abre un panel de conversación. Está escrito en **JavaScript puro (sin frameworks)** y se entrega como **un único archivo**: `build/chatbot.min.js`.

Flujo funcional:

1. El usuario abre el panel → mensaje de bienvenida.
2. Perfilado con botones: **provincia** → **área formativa**.
3. Aparece una caja de texto para preguntar.
4. Cada pregunta se envía a la IA (`/api/chat/ask/`) o a un mock.
5. Si la IA no sabe (`fallback_activado: true`) o hay oportunidad comercial (`requiere_accion_comercial: true`), se oculta la caja de texto y se muestra el **formulario de lead**, que se envía a `/api/chat/lead/`.

---

## 2. Estructura del proyecto

```
widget/
├── src/
│   ├── chatbot.js        ← FUENTE REAL del widget (HTML + CSS + lógica)
│   └── chatbot.css       ← CSS aparte (ver §8, hoy NO se usa)
├── static/
│   ├── mock_ask.json            ← respuesta normal simulada de /api/chat/ask/
│   ├── mock_ask_fallback.json   ← respuesta con fallback_activado: true
│   └── mock_lead.json           ← respuesta simulada de /api/chat/lead/
├── build/
│   └── chatbot.min.js    ← artefacto final que se incluye en la web
├── build.mjs             ← script de build (esbuild)
├── package.json          ← solo esbuild como devDependency
├── test.html             ← página mínima de pruebas
└── README.md             ← resumen rápido de interruptores y contrato de lead
```

`node_modules/` no se versiona; se regenera con `npm ci`.

---

## 3. Cómo ejecutarlo

### 3.1 Probar rápido en local

**Importante:** no abras `test.html` con doble clic (`file://`). Los mocks se piden con `fetch("/static/...")`, una ruta absoluta que necesita un servidor HTTP.

Desde la carpeta `widget/`:

```bash
python3 -m http.server 8000
# o: npx http-server -p 8000
```

Abre `http://localhost:8000/test.html`. Como el servidor cuelga de `widget/`, la ruta `/static/mock_ask.json` resuelve a `widget/static/mock_ask.json` y los mocks funcionan.

### 3.2 Regenerar el build

```bash
cd widget
npm ci
npm run build      # genera build/chatbot.min.js
```

`test.html` carga `./build/chatbot.min.js`, así que **cualquier cambio en `src/` exige volver a ejecutar el build** para verlo.

> Nota: el `build/chatbot.min.js` que viene en el ZIP es una copia **idéntica, sin minificar** del fuente (así se puede probar sin instalar nada). `npm run build` lo sustituye por la versión minificada.

### 3.3 Integrarlo en la web real

Una sola línea antes de `</body>`:

```html
<script async src="/static/chatbot.min.js"></script>
```

(Ajusta la ruta a donde Django sirva el archivo.) El script se autoejecuta, crea su propio contenedor y no necesita nada más.

---

## 4. Interruptores de entorno (en `src/chatbot.js`, líneas ~11-30)

| Constante | Valor | Efecto |
|---|---|---|
| `USAR_IA` | `false` | Chat **sin IA**: respuestas locales por palabras clave (`respuestaLocal`). |
| `USAR_IA` | `true` | Usa el contrato de `/api/chat/ask/` (real o mock según `MOCK_API`). |
| `MOCK_API` | `true` | `ask` y `lead` se sirven desde los JSON de `static/`. Sin backend. |
| `MOCK_API` | `false` | Llamadas reales con `fetch` POST a `/api/chat/ask/` y `/api/chat/lead/`. |
| `MOCK_SCENARIO` | `"ok"` | Con mock, responde `mock_ask.json` (conversación normal). |
| `MOCK_SCENARIO` | `"fallback"` | Con mock, responde `mock_ask_fallback.json` → aparece el formulario de lead. |
| `MOCK_BASE` | `"/static/"` | Carpeta desde la que se piden los mocks. |

**Estado en el ZIP:** `USAR_IA = true`, `MOCK_API = true`, `MOCK_SCENARIO = "ok"`.
⚠️ **Antes de desplegar a producción hay que poner `MOCK_API = false`**, o el widget seguirá devolviendo "Texto de prueba del LLM simulado...".

Receta de pruebas:

| Quiero probar… | Configuración |
|---|---|
| Perfilado + chat sin backend ni IA | `USAR_IA=false` |
| Conversación con mock | `USAR_IA=true, MOCK_API=true, MOCK_SCENARIO="ok"` |
| Formulario de leads | `USAR_IA=true, MOCK_API=true, MOCK_SCENARIO="fallback"` |
| Integración real con Django | `USAR_IA=true, MOCK_API=false` |

---

## 5. Contratos de API

### `POST /api/chat/ask/`

Petición (la construye `consultarIA`):

```json
{
  "pregunta": "¿Qué cursos hay?",
  "provincia": "Salamanca",
  "campo_estudio": "Sanidad",
  "sesion_uuid": "uuid"
}
```

Respuesta esperada:

```json
{
  "texto_respuesta": "…",
  "requiere_accion_comercial": false,
  "fallback_activado": false
}
```

El widget también acepta la clave `respuesta` como alternativa a `texto_respuesta` por si el backend la cambia. Si la respuesta HTTP no es 2xx, lee `data.error` para el mensaje.

### `POST /api/chat/lead/`

```json
{
  "nombre": "string",
  "email": "string",
  "telefono": "string",
  "provincia": "string",
  "campo_estudio": "string",
  "colectivo": "string",
  "consentimiento_rgpd": true,
  "sesion_uuid": "uuid"
}
```

- Email y teléfono son **alternativos**: al menos uno es obligatorio (se valida en el widget; el backend debe validarlo también).
- `colectivo` es obligatorio porque lo exige el contrato.
- Los campos de contacto que el usuario deja vacíos se envían como `""`, no se omiten.
- Respuesta esperada: `{ "ok": true, "mensaje": "…" }`. El widget muestra `mensaje` al usuario.

---

## 6. Decisiones de diseño y su porqué

**Vanilla JS, cero dependencias.** El widget se inserta en webs ajenas. Un framework añadiría peso, riesgo de conflicto de versiones y complejidad de integración. Un solo `<script async>` es lo mínimo posible.

**IIFE (`(function(){ ... })()`).** Mantiene todas las variables fuera del ámbito global. Evita choques con el JS de la web anfitriona.

**Shadow DOM (`attachShadow({ mode: "open" })`).** Aísla el CSS en ambos sentidos: los estilos de la página no rompen el widget y los del widget no se filtran a la página. Por eso `:host { all: initial; }` resetea lo heredado. Los ids internos (`$("chatbot-toggle")`) se buscan con `root.getElementById`, no con `document`.

**Todo en un archivo.** Una sola petición de red, un solo artefacto que versionar y cachear. Por eso `build.mjs` está pensado para inyectar el CSS dentro del JS (ver §8).

**`z-index: 2147483647`.** Es el máximo permitido; garantiza que el widget quede encima de menús y banners de cookies de la web anfitriona.

**UUID de sesión en `sessionStorage`.** Identifica la conversación para el backend (la app `leads` usa `sesion_uuid` **sin ForeignKey**, así que no hace falta que exista un modelo de sesión previo). `sessionStorage` desaparece al cerrar la pestaña, lo que encaja con la privacidad: no hay identificador persistente. Si `crypto.randomUUID` no existe, hay un fallback con `Date.now()` + aleatorio.

**Los mocks sustituyen al backend (sección 5 de la guía del proyecto).** El backend RAG lo desarrolla otra persona (Dev A). Con `MOCK_API` el frontend avanza y se prueba el flujo completo sin esperar. Hay dos mocks de `ask` precisamente para poder forzar el camino del formulario de leads.

**`pedirRespuestaIA` y `enviarLead` son los únicos puntos que tocan la red.** Todo el resto del widget no sabe si habla con un mock o con Django. Cambiar de entorno es cambiar una constante. `consultarIA` traduce el contrato del backend al vocabulario interno (`entendida`, `solicitarDatos`, `texto`).

**Perfilado con botones, no texto libre.** Provincia y área tienen valores cerrados (`PROVINCIAS`, `CURSOS`). Se obtienen datos limpios y comparables para el lead y para filtrar en el RAG, sin depender de que la IA interprete texto.

**Doble disparador del formulario de lead.**
- Inmediato si `fallback_activado` o `requiere_accion_comercial` son `true`.
- Si la IA "no entiende" (`entendida === false`): 1.er intento → pide reformular; 2.º intento → formulario. Así no se frustra al usuario con un bucle.

**Consentimiento RGPD explícito.** El checkbox es obligatorio y se envía como `consentimiento_rgpd`. El texto de privacidad enlaza a `/politica-de-privacidad/` (ruta del sitio anfitrión, ajustar si cambia).

**Uso de `textContent` para mensajes.** Evita XSS: el texto de la IA o del usuario nunca se interpreta como HTML. (El único `innerHTML` con contenido variable es el indicador de "escribiendo", que es estático.)

**Accesibilidad.** `role="dialog"`, `aria-modal`, `aria-labelledby`, `aria-expanded` en el botón, `aria-live="polite"` en los mensajes, etiquetas `<label>` en el formulario y gestión del foco al abrir/cerrar.

---

## 7. Cómo funciona por dentro (mapa del código)

Flujo de estado: `state.etapa` pasa por `provincia` → `campo` → `pregunta`.

| Función | Para qué sirve |
|---|---|
| `getSession()` | Lee o crea el UUID en `sessionStorage`. |
| `addMessage(texto, tipo)` | Añade burbuja `bot` o `user` y hace scroll. |
| `showTyping()` / `hideTyping()` | Indicador de "escribiendo". |
| `showOptions(lista)` / `clearOptions()` | Botones de perfilado. |
| `start()` | Reinicia el estado, limpia mensajes/formularios y muestra la bienvenida. |
| `selectOption(valor)` | Avanza de etapa en el perfilado. |
| `respuestaLocal(pregunta)` | Respuestas por palabras clave (modo `USAR_IA=false`). |
| `pedirRespuestaIA(payload)` | Mock o `fetch` real a `/api/chat/ask/`. |
| `consultarIA(pregunta)` | Orquesta y normaliza la respuesta. |
| `procesarPregunta(pregunta)` | Ciclo completo de una pregunta: typing → respuesta → ¿lead? |
| `showLead()` | Oculta la caja de texto y muestra el formulario. |
| `enviarLead(payload)` / `sendLead()` | Mock o `fetch` real a `/api/chat/lead/`. |

Eventos: `Enter` envía (Shift+Enter hace salto de línea); el botón flotante alterna abrir/cerrar; la `×` cierra.

---

## 8. Puntos pendientes y discrepancias conocidas

Revisados leyendo el código tal como está en el ZIP. Conviene resolverlos antes de producción.

1. **`src/chatbot.css` no se usa.** `build.mjs` busca el marcador `"__CHATBOT_CSS__"` en `chatbot.js` para inyectar el CSS minificado, pero ese marcador **no existe**: el CSS vive duplicado dentro de `chatbot.js` en la constante `STYLES`. Hoy el build solo minifica el JS y el CSS "bueno" (`chatbot.css`, que además es distinto: botón de 62 px, `#1d4ed8`, etc.) se ignora. Decidir una fuente única: o se edita `STYLES` y se borra `chatbot.css`, o se restaura el marcador (`<style>${"__CHATBOT_CSS__"}</style>`) y se elimina `STYLES`.
2. **No hay focus trap real.** Se mueve el foco al abrir/cerrar, pero con `Tab` el foco puede salir del panel aunque el atributo sea `aria-modal="true"`. Es un requisito de accesibilidad definido para el proyecto.
3. **`Escape` solo cierra desde el `textarea`.** Si el foco está en un botón de opción o en el formulario de lead, no cierra.
4. **El reinicio al reabrir no está implementado como se decidió.** La decisión de producto fue "cada vez que se abre, conversación nueva y UUID nuevo". El código actual solo llama a `start()` la primera vez (si no hay mensajes) y reutiliza el UUID guardado en `sessionStorage` mientras dure la pestaña. Además, `getSession()` se ejecuta una sola vez al cargar. Para cumplir la decisión: en el click de apertura llamar a `start()` siempre y regenerar el UUID (borrar `SESSION_KEY` y volver a asignar `state.sessionUuid`).
5. **El `placeholder` del `textarea` no se ve.** El `<textarea>` del template contiene saltos de línea y espacios entre las etiquetas, lo que cuenta como valor; el placeholder solo aparece con el campo vacío. Cerrar la etiqueta pegada: `<textarea ...></textarea>`.
6. **`MOCK_API = true` por defecto** (ver §4). Riesgo de desplegar con mocks.
7. **`MOCK_BASE = "/static/"`** asume que Django (o el servidor) sirve los JSON en esa ruta; fuera de eso, el modo mock falla con "No se encontró el archivo de prueba".
8. **Sin CSRF.** Si los endpoints de Django usan protección CSRF por sesión, los `fetch` POST necesitarán el token (o los endpoints tendrán que ser `csrf_exempt` con otra protección). Coordinar con el backend.
9. **Rutas absolutas** `/api/chat/...` y `/politica-de-privacidad/`: el widget debe servirse desde el mismo origen o habría que parametrizar la URL base y configurar CORS.
10. **Validación solo en cliente.** El backend debe revalidar (email/teléfono alternativos, RGPD, longitud de campos).

---

## 9. Receta para añadir cosas

- **Nueva pregunta de perfilado** (p. ej. situación laboral): añadir la lista de opciones, un campo en `state`, una etapa nueva en `selectOption` y, si procede, incluirlo en los payloads de `ask` y `lead` (y acordarlo con el backend).
- **Cambiar provincias o áreas:** editar `PROVINCIAS` y `CURSOS` al principio de `chatbot.js`.
- **Cambiar estilos:** ver punto 1 de §8 antes de tocar nada.
- **Cambiar de mock a IA real:** `MOCK_API = false`, `npm run build`, redesplegar `chatbot.min.js`.

---

## 10. Lista de comprobación antes de publicar

- [ ] `MOCK_API = false` y `USAR_IA = true`
- [ ] `npm ci && npm run build` ejecutado; se despliega `build/chatbot.min.js` minificado
- [ ] Endpoints `/api/chat/ask/` y `/api/chat/lead/` responden con el contrato de §5
- [ ] CSRF/CORS resueltos con el backend
- [ ] Enlace de política de privacidad correcto
- [ ] Prueba manual: perfilado, pregunta normal, fallback → lead, lead enviado, teclado (Tab/Enter/Esc), móvil (<480 px)