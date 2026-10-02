# Documentación funcional: app `widget`

**Proyecto:** Chatbot de orientación formativa
**Componente:** Cliente / Frontend puro (Vanilla JS + CSS encapsulado)
**Archivo fuente:** `widget/chatbot.js` → **salida:** `widget/build/chatbot.min.js`
**Estado:** Fase de perfilado funcional; integración de IA pendiente

---

## 1. Resumen

El widget es un chatbot embebible que se muestra como un botón flotante en la esquina inferior derecha de la página. Al pulsarlo se despliega un panel de conversación que:

1. Da un mensaje de bienvenida.
2. Perfila al usuario mediante preguntas con botones (provincia, curso, situación laboral, experiencia y objetivo).
3. Abre una caja de texto libre para que el usuario formule su consulta, que se envía al backend (`/api/chat/ask/`).
4. Si el backend no entiende la consulta de forma reiterada, muestra un formulario de contacto que envía un lead a `/api/chat/lead/`.

No usa frameworks ni dependencias externas.

---

## 2. Arquitectura

| Aspecto | Implementación |
|---|---|
| Lenguaje | JavaScript vanilla, sin frameworks |
| Aislamiento de variables | IIFE `(function () { "use strict"; ... })();` |
| Aislamiento de estilos y DOM | Shadow DOM (`attachShadow({ mode: "open" })`) sobre un contenedor `#chatbot-widget` |
| CSS | Encapsulado dentro del Shadow DOM mediante la constante `STYLES`, inyectada en una etiqueta `<style>` de la plantilla |
| Salida | Un único archivo `widget/build/chatbot.min.js` |
| Integración | `<script async src=".../chatbot.min.js"></script>` antes del cierre de `</body>` |

**Creación del contenedor.** Al cargarse, el script busca un elemento con id `chatbot-widget`. Si no existe, lo crea y lo añade al `body`. Después crea (o reutiliza) su Shadow Root y renderiza la plantilla (`TEMPLATE`).

**Aislamiento.** Ni los estilos de la página anfitriona afectan al widget, ni los del widget a la página. Ninguna variable queda expuesta en el ámbito global.

---

## 3. Estructura de la interfaz

Elementos de la plantilla, referenciados en el objeto `ui`:

| Elemento | ID | Función |
|---|---|---|
| Botón flotante | `chatbot-toggle` | Abre el chatbot. Usa `aria-expanded` y `aria-controls` |
| Panel | `chatbot-panel` | Contenedor con `role="dialog"` y `aria-modal="true"`; oculto por defecto |
| Botón de cierre | `chatbot-close` | Cierra el panel |
| Zona de mensajes | `chatbot-messages` | Historial de la conversación (`aria-live="polite"`) |
| Zona de opciones | `chatbot-options` | Botones de respuesta del perfilado (`role="group"`) |
| Formulario de pregunta | `chatbot-form` | Textarea (`chatbot-question`) y botón de envío (`chatbot-send`) |
| Formulario de lead | `chatbot-lead` | Campos nombre, email, teléfono y botón `chatbot-lead-submit` |

Los mensajes se pintan como párrafos con las clases `chatbot-message--bot` y `chatbot-message--user`. Se usa `textContent`, por lo que el contenido nunca se interpreta como HTML (previene XSS).

---

## 4. Estado de la aplicación (`state`)

| Campo | Descripción |
|---|---|
| `isOpen` | Si el panel está abierto |
| `isLoading` | Si hay una petición en curso (bloquea envíos duplicados) |
| `sessionUuid` | UUID de la sesión actual |
| `etapa` | Etapa actual del flujo (ver sección 5) |
| `provincia`, `campoEstudio`, `colectivo`, `experienciaProfesional`, `objetivo` | Respuestas del perfilado |
| `pregunta` | Última consulta escrita por el usuario |
| `nombre`, `email`, `telefono` | Datos del formulario de contacto |
| `fallbackActivado` | Si se ha llegado al fallback definitivo |
| `fallbackIntentos` | Contador de consultas no entendidas (0, 1 o 2) |

---

## 5. Flujo conversacional

El flujo se define en la tabla `FLOW`. Cada etapa indica el texto del bot, las opciones (o texto libre), el campo del estado donde se guarda la respuesta y la etapa siguiente.

| # | Etapa | Pregunta del bot | Tipo | Opciones | Campo |
|---|---|---|---|---|---|
| 1 | `provincia` | ¿En qué provincia estás? | Botones | Salamanca, Ávila, Segovia, Valladolid, Zamora, León, Palencia, Burgos, Soria | `provincia` |
| 2 | `campo_estudio` | ¿Qué curso estás buscando? | Botones | Administración y gestión, Comercio y marketing, Informática y comunicaciones, Sanidad, Otro | `campoEstudio` |
| 3 | `colectivo` | ¿En este momento estás trabajando? | Botones | Sí, No | `colectivo` |
| 4 | `experiencia` | ¿En qué tipo de trabajo o área profesional tienes más experiencia? | Botones | Administración, Comercio, Atención al cliente, Informática, Sanidad, Educación, Industria, Hostelería, Construcción, Transporte, Otro | `experienciaProfesional` |
| 5 | `objetivo` | ¿Qué te gustaría conseguir con esta formación? | Botones | Mejorar en mi trabajo, Cambiar de sector, Encontrar empleo, Otro | `objetivo` |
| 6 | `pregunta` | Gracias, ya tengo lo básico. Cuéntame, ¿en qué puedo ayudarte? | Texto libre | — | `pregunta` |

**Mecánica de una respuesta con botones:**

1. El usuario pulsa una opción (`selectOption`).
2. Se limpian las opciones y se muestra su respuesta como mensaje de usuario.
3. `processOptionAnswer` guarda el valor en el campo correspondiente y avanza a la etapa siguiente.
4. `askNextQuestion` muestra la siguiente pregunta y sus botones.

Mientras hay botones visibles, la caja de texto permanece oculta. Al llegar a la etapa `pregunta` se oculta la zona de opciones y se muestra la caja de texto.

---

## 6. Ciclo de vida del chatbot

### Apertura (`open`)
Al pulsar el botón flotante: marca el panel como abierto, lo muestra, actualiza `aria-expanded` y ejecuta `resetConversation()`.

### Reinicio (`resetConversation`)
Cada apertura comienza una conversación nueva:

- Borra todos los mensajes, las opciones y los campos de texto.
- Oculta ambos formularios.
- Restablece el estado completo (etapa `provincia`, respuestas a `null`, `fallbackIntentos = 0`).
- Genera un UUID de sesión nuevo.
- Muestra el mensaje de bienvenida y lanza la primera pregunta.

### Cierre (`close`)
Oculta el panel, actualiza `aria-expanded` y devuelve el foco al botón flotante. **No borra la conversación**; el borrado se produce al volver a abrir.

### Sesión
- Clave en `sessionStorage`: `chatbot_session_uuid`.
- Se genera con `crypto.randomUUID()`; si no está disponible, se usa un identificador alternativo basado en la fecha y un número aleatorio.
- Se envía como `sesion_uuid` en todas las llamadas al backend para vincular consulta, perfil y lead.

---

## 7. Integración con el backend

### 7.1 `POST /api/chat/ask/`

Se invoca en `sendQuestion()` cuando el usuario envía su consulta.

**Petición (JSON):**

```json
{
  "pregunta": "string",
  "provincia": "string",
  "campo_estudio": "string",
  "colectivo": "string",
  "experiencia_profesional": "string",
  "objetivo": "string",
  "sesion_uuid": "string"
}
```

**Respuesta esperada (JSON):**

| Campo | Uso en el widget |
|---|---|
| `texto_respuesta` | Si existe, se muestra como mensaje del bot |
| `fallback_activado` | Booleano que dispara la lógica de fallback |
| `error` | En respuestas no exitosas, se usa como mensaje del error lanzado |

### 7.2 `POST /api/chat/lead/`

Se invoca en `sendLead()` al enviar el formulario de contacto.

**Petición (JSON):**

```json
{
  "nombre": "string",
  "email": "string",
  "telefono": "string",
  "provincia": "string",
  "campo_estudio": "string",
  "colectivo": "string",
  "experiencia_profesional": "string",
  "objetivo": "string",
  "sesion_uuid": "string"
}
```

**Respuesta esperada:** el campo `mensaje` se muestra al usuario; si no viene, se muestra un texto de agradecimiento por defecto. En caso de error se usa el campo `error`.

---

## 8. Lógica de fallback

El widget lee `fallback_activado` de la respuesta de `/api/chat/ask/`. La lógica está pensada para dar una segunda oportunidad antes de derivar a una persona.

```
Respuesta del backend
├── fallback_activado = false
│     → reinicia fallbackIntentos a 0
│     → deja la caja de texto abierta para seguir preguntando
│
└── fallback_activado = true
      ├── 1.er fallo (fallbackIntentos = 1)
      │     → "No he podido identificar exactamente lo que necesitas.
      │        ¿Podrías explicármelo de otra manera?"
      │     → mantiene la caja de texto
      │
      └── 2.º fallo (fallbackIntentos ≥ 2)
            → informa de que se pondrá en contacto al equipo
            → oculta la caja de texto
            → muestra el formulario de contacto (showLeadForm)
```

**Formulario de contacto (`showLeadForm`).** Oculta la caja de texto y las opciones, y muestra el formulario con nombre, email y teléfono (los tres obligatorios, con `autocomplete` apropiado). Al enviarlo:

1. Se valida que los tres campos estén rellenos.
2. Se guardan en el estado y se muestran como mensajes del usuario.
3. `sendLead()` los envía junto con el perfil y el UUID de sesión.
4. Si va bien, se muestra el mensaje de confirmación, se oculta el formulario y la etapa pasa a `finalizado`, bloqueando nuevos envíos de texto.

> **Nota sobre el cumplimiento de la especificación.** La especificación habla de "destruir o esconder" la caja de texto y "montar dinámicamente" el formulario. El widget implementa la variante de **esconder y mostrar**: el formulario existe en la plantilla desde el inicio, oculto con el atributo `hidden`.

---

## 9. Accesibilidad y navegación por teclado

| Aspecto | Implementación |
|---|---|
| Rol del panel | `role="dialog"`, `aria-modal="true"`, `aria-labelledby="chatbot-title"` |
| Botón flotante | `aria-label`, `aria-expanded` actualizado al abrir/cerrar, `aria-controls` |
| Mensajes | Región `aria-live="polite"`: los lectores de pantalla anuncian cada mensaje nuevo |
| Opciones | Grupo con `role="group"` y `aria-label`; cada botón con su `aria-label` |
| Foco al avanzar | Se enfoca el primer botón de opciones o la caja de texto, según la etapa |
| Cierre | Tecla **Esc** cierra el panel y devuelve el foco al botón flotante |
| Envío | **Enter** envía la pregunta; **Shift + Enter** inserta salto de línea |
| Focus trap | Con **Tab** y **Shift + Tab** el foco circula solo por los elementos visibles y habilitados dentro del panel |

El focus trap considera únicamente elementos visibles del panel, de modo que se adapta a cada etapa (botones, textarea o formulario de lead).

---

## 10. Gestión de errores y estados de carga

- `isLoading` evita envíos duplicados (consulta o lead) mientras hay una petición en curso.
- Los botones de envío se deshabilitan durante la petición y se rehabilitan en el bloque `finally`.
- Errores de red o respuestas no exitosas muestran un mensaje genérico al usuario ("No hemos podido procesar tu consulta" / "No hemos podido enviar tus datos") y el detalle técnico se registra en `console.error`.
- Tras un error, el usuario puede reintentar sin reiniciar el chat.

---

## 11. Matriz de cumplimiento frente a la especificación

| Requisito | Estado | Observaciones |
|---|---|---|
| Vanilla JS y CSS encapsulado | Cumplido | Shadow DOM + IIFE |
| Salida en `chatbot.min.js` | Depende del build | El código está preparado como archivo único |
| Integración con `<script async>` | Cumplido | No depende del orden de carga |
| Botón flotante inferior derecha | Cumplido | Posición definida en el CSS |
| Panel colapsable | Cumplido | |
| Caja de texto libre | Cumplido | Disponible tras el perfilado |
| Selectores `provincia`, `campo_estudio`, `colectivo` | Cumplido con variación de diseño | Implementados como preguntas guiadas con botones, junto a `experiencia` y `objetivo` |
| Aislamiento de variables | Cumplido | |
| Navegación por teclado, ARIA y focus trap | Cumplido | Ver sección 9 |
| UUID de sesión en `sessionStorage` | Cumplido con variación | Se regenera en cada apertura del chat (decisión de diseño) |
| Llamada a `/api/chat/ask/` | Cumplido | |
| Lectura de `fallback_activado` | Cumplido | Con lógica de dos intentos |
| Formulario de leads a `/api/chat/lead/` | Parcial | Falta el consentimiento RGPD (ver sección 12) |

---

## 12. Pendientes y puntos a validar

1. **Consentimiento RGPD.** La especificación del backend rechaza con `HTTP 400` los leads con `consentimiento_rgpd = false`, pero el formulario no tiene casilla de consentimiento y `sendLead()` no envía ese campo. Hay que añadir una casilla obligatoria y enviar `consentimiento_rgpd` en el payload.
2. **Token CSRF.** Si los endpoints de Django no están exentos de CSRF, las peticiones POST devolverán 403. Hay que decidir entre eximir los endpoints o enviar el token.
3. **Origen de las peticiones.** Las rutas `/api/chat/...` son relativas, por lo que funcionan si el widget se sirve desde el mismo dominio que el backend. Para incrustarlo en dominios distintos se necesitaría una URL base configurable y CORS.
4. **Campos adicionales del lead.** El widget envía `experiencia_profesional` y `objetivo`; hay que confirmar que el modelo `Lead` los almacena o decidir si se descartan.
5. **Valor del campo `colectivo`.** Hoy se envía "Sí" o "No" (pregunta de situación laboral). Conviene acordar con el backend si se transforma a categorías explícitas.
6. **Indicador de carga.** No hay indicador visual ("escribiendo...") mientras se espera respuesta.
7. **Disponibilidad de `sessionStorage`.** No se controlan los entornos donde el acceso a `sessionStorage` lanza excepción (algunos modos de navegación privada restrictivos).
8. **Inyección del CSS en el build.** La constante `STYLES` debe contener el CSS real o ser reemplazada por el proceso de build; si queda como marcador de posición, el widget se muestra sin estilos.

---

## 13. Siguiente fase: integración de IA

La fase de perfilado queda completa y el contexto del usuario está disponible en el estado. La integración de IA afectará principalmente a `/api/chat/ask/`:

- El payload ya incluye el perfil completo y la sesión, que pueden usarse como contexto del modelo.
- El widget no necesita cambios estructurales: basta con que el backend devuelva `texto_respuesta` y `fallback_activado` con el mismo contrato.
- Mientras la IA no esté disponible, el endpoint puede devolver una respuesta fija con `fallback_activado: false` para probar el ciclo completo.
