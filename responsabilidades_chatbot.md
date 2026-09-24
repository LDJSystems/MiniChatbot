# Responsabilidades y delegación — Chatbot CEFYE
> Django MVT · Dos desarrolladores · Trabajo en paralelo desde el inicio

---

## Índice

- [Responsabilidades y delegación — Chatbot CEFYE](#responsabilidades-y-delegación--chatbot-cefye)
  - [Índice](#índice)
  - [1. Criterios de reparto](#1-criterios-de-reparto)
  - [2. Apps de Django y propietario](#2-apps-de-django-y-propietario)
  - [3. Dev A — detalle de responsabilidades](#3-dev-a--detalle-de-responsabilidades)
    - [3.1 App `knowledge`](#31-app-knowledge)
    - [3.2 App `rag`](#32-app-rag)
    - [3.3 App `ingestion`](#33-app-ingestion)
    - [3.4 Infra / DevOps](#34-infra--devops)
  - [4. Dev B — detalle de responsabilidades](#4-dev-b--detalle-de-responsabilidades)
    - [4.1 App `sessions`](#41-app-sessions)
    - [4.2 App `leads`](#42-app-leads)
    - [4.3 App `telemetry`](#43-app-telemetry)
    - [4.4 App `widget`](#44-app-widget)
  - [5. Contratos compartidos — acordar antes de arrancar](#5-contratos-compartidos--acordar-antes-de-arrancar)
    - [5.1 Contrato del payload de `/api/chat/ask/`](#51-contrato-del-payload-de-apichatask)
    - [5.2 Contrato del payload de `/api/chat/lead/`](#52-contrato-del-payload-de-apichatlead)
    - [5.3 Esquema relacional — revisión conjunta](#53-esquema-relacional--revisión-conjunta)
  - [6. Orden de entrega y dependencias](#6-orden-de-entrega-y-dependencias)
    - [Fase 1 — Base (semana 1, en paralelo)](#fase-1--base-semana-1-en-paralelo)
    - [Fase 2 — Núcleo (semana 2, en paralelo)](#fase-2--núcleo-semana-2-en-paralelo)
    - [Fase 3 — Integración (semana 3)](#fase-3--integración-semana-3)
  - [7. Gestión de ramas y revisiones](#7-gestión-de-ramas-y-revisiones)
    - [Estrategia de ramas](#estrategia-de-ramas)
    - [Reglas de convivencia en el repositorio](#reglas-de-convivencia-en-el-repositorio)
  - [8. Única dependencia cross-dev y cómo desbloquearla](#8-única-dependencia-cross-dev-y-cómo-desbloquearla)

---

## 1. Criterios de reparto

| Criterio | Aplicación |
|---|---|
| **Complejidad técnica** | Las apps con mayor complejidad (RAG, FTS, ETL, infra) van a Dev A |
| **Autonomía de Dev B** | Sus apps tienen lógica acotada y bien definida en el spec, sin necesidad de supervisión constante |
| **Ambos tocan backend** | Cada desarrollador es dueño completo de su app: modelo, vista y template/admin |
| **Fronteras de git limpias** | Cada app vive en su propio directorio Django; conflictos de merge prácticamente imposibles |
| **Un solo punto de fricción** | La única dependencia cross-dev se mockea desde el primer día para que Dev B no espere |

---

## 2. Apps de Django y propietario

| App | Propietario | Dominio DB | Tablas que gestiona |
|---|---|---|---|
| `knowledge` | **Dev A** | Conocimiento | `BaseConocimiento` · `StagingCursos` |
| `rag` | **Dev A** | — | Sin tabla propia · orquesta pipeline |
| `ingestion` | **Dev A** | Conocimiento | `StagingCursos` (escritura ETL) |
| `sessions` | **Dev B** | Volátil | `Sesion` · `Mensaje` |
| `leads` | **Dev B** | Persistente | `Lead` |
| `telemetry` | **Dev B** | Persistente | `ConsultaFallida` · `ContadorDemanda` |
| `widget` | **Dev B** | — | Sin tabla · frontend Vanilla JS |
| `infra` | **Dev A** | — | Docker · Nginx · variables de entorno |

> **Regla general:** quien es propietario de una app es el único que crea o modifica sus migraciones. Si necesitas datos de otra app, los pides a través de la API o del ORM de solo lectura, nunca tocas sus migraciones.

---

## 3. Dev A — detalle de responsabilidades

### 3.1 App `knowledge`

Es la primera entrega de Dev A porque desbloquea todo lo demás. Sin esta app no hay RAG, no hay búsqueda y no hay widget funcional.

**Modelos:**

| Modelo | Tabla | Responsabilidad |
|---|---|---|
| `BaseConocimiento` | `base_conocimiento` | Definir todos los campos, los índices B-Tree y GIN, el campo `vector_busqueda` |
| `StagingCursos` | `staging_cursos` | Tabla de buffer del ETL con campo `hash_contenido` único |

**Vistas / lógica:**

- Vista de administración en Django Admin para `BaseConocimiento`: listado filtrable por `provincia`, `campo_estudio` y `colectivo`, con la columna `activo` editable en línea.
- Vista de administración para `StagingCursos`: listado con campo `estado` (pendiente / validado / descartado) editable.
- Comando de gestión (`management/commands/`) para cargar datos iniciales desde JSON/CSV a `BaseConocimiento`.

**Trigger PostgreSQL:**

- Redactar y ejecutar la migración que crea `tg_bc_actualizar_vector` en `RunSQL`.
- El trigger recalcula `vector_busqueda` en cada `INSERT` y `UPDATE` usando `setweight` con pesos A (título) y B (contenido), en español (`pg_catalog.spanish`).
- Los filtros estrictos (`provincia`, `campo_estudio`, `colectivo`) no entran en el vector.

---

### 3.2 App `rag`

El núcleo del chatbot. Orquesta el pipeline completo: recibe la consulta, ejecuta el Retriever híbrido sobre `BaseConocimiento` y llama a Ollama para generar la respuesta.

**Sin modelo propio.** Lee `BaseConocimiento` del ORM de `knowledge`.

**Vistas (endpoints API):**

| Endpoint | Método | Responsabilidad |
|---|---|---|
| `/api/chat/ask/` | `POST` | Recibir payload híbrido · ejecutar Retriever · llamar Ollama · devolver respuesta con flags |

**Lógica interna:**

- `retriever.py` — Fase 1: pre-filtro categórico opcional sobre `provincia`, `campo_estudio` y `colectivo`. Fase 2: FTS con `SearchRank` y umbral `rank >= 0.12`.
- `generator.py` — Empaqueta el contexto validado y llama al demonio Ollama local. Si el Retriever devuelve cero resultados, no se llama a Ollama: se activa el fallback.
- `serializers.py` — Valida el payload entrante. Devuelve JSON con `texto_respuesta`, `requiere_accion_comercial` (bool) y `fallback_activado` (bool).

**Responsabilidades de seguridad:**

- Aplicar `django-ratelimit` sobre `/api/chat/ask/` por IP.
- Configurar `django-cors-headers` para aceptar solo dominios oficiales de CEFYE.

---

### 3.3 App `ingestion`

Pipeline ETL desacoplado. Descarga datos del scraping a `StagingCursos`, los valida y ejecuta el upsert a `BaseConocimiento`.

**Modelos:** ninguno propio. Escribe en `StagingCursos` (de `knowledge`) y lee/escribe en `BaseConocimiento`.

**Tareas Celery:**

| Tarea | Frecuencia | Responsabilidad |
|---|---|---|
| `tarea_scraping` | Celery Beat · horario de baja concurrencia | Recorre la web pública de CEFYE con throttling. Inserta en `StagingCursos` con `hash_contenido` para evitar duplicados |
| `tarea_upsert` | Tras `tarea_scraping` | Lee registros con `estado = 'pendiente'` de staging, los normaliza, ejecuta upsert en `BaseConocimiento` y marca `estado = 'validado'` |

**Lógica:**

- Normalización de las variables categóricas (`provincia`, `campo_estudio`, `colectivo`) a los valores controlados del vocabulario.
- El upsert desencadena automáticamente el recálculo del vector GIN gracias al trigger definido en `knowledge`.

---

### 3.4 Infra / DevOps

**Archivos bajo responsabilidad exclusiva de Dev A:**

| Archivo | Contenido |
|---|---|
| `docker-compose.yml` | 4 servicios: `db` (PostgreSQL 15) · `ollama` · `web` (Django + Gunicorn) · `nginx` |
| `.env.example` | Plantilla de variables de entorno sin valores reales |
| `nginx/nginx.conf` | Proxy inverso · HTTPS · servicio de estáticos incluyendo `chatbot.min.js` |
| `requirements.txt` | Solo dependencias top-level: Django 6.x · psycopg[c] · gunicorn · django-environ · django-cors-headers · django-ratelimit · ollama · celery |
| `Dockerfile` | Imagen de producción del servicio `web` |

**Reglas:**

- El puerto 5432 de `db` no se expone al exterior.
- El puerto 11434 de `ollama` no se expone al exterior.
- Solo `nginx` tiene puertos públicos (80 y 443).
- Los pesos del modelo LLM se cachean en el volumen `ollama_models` para no descargarlos en cada redespliegue.

---

## 4. Dev B — detalle de responsabilidades

### 4.1 App `sessions`

Primera entrega de Dev B. Es la base que desbloquea `leads` y da contexto al widget.

**Modelos:**

| Modelo | Tabla | Responsabilidad |
|---|---|---|
| `Sesion` | `sesion` | UUID como PK · filtros categóricos opcionales · `ultima_actividad` para el cron |
| `Mensaje` | `mensaje` | FK dura a `Sesion` con `ON DELETE CASCADE` · campo `rol` con `CheckConstraint` |

**Vistas / lógica:**

- Vista interna `crear_o_recuperar_sesion` — recibe el UUID del `sessionStorage` del navegador. Si no existe, crea una nueva sesión. Si existe, actualiza `ultima_actividad`.
- No hay endpoint público propio: la sesión se crea/recupera desde el endpoint `ask/` de `rag`.

**Cron job (gestión de purga):**

- Comando de gestión `purgar_sesiones_inactivas` que borra `Sesion` con `ultima_actividad` anterior al umbral configurado en `.env`.
- Al borrar la sesión, PostgreSQL elimina sus `Mensaje` en cascada automáticamente.
- Este comando lo registra Dev A en el `docker-compose.yml` como servicio cron o en Celery Beat.

**Vista Django Admin:**

- Listado de sesiones activas con última actividad y número de mensajes. Solo lectura.

---

### 4.2 App `leads`

Captura el contacto comercial cuando el usuario elige la vía asistida.

**Modelos:**

| Modelo | Tabla | Responsabilidad |
|---|---|---|
| `Lead` | `lead` | Todos los campos · los tres `CheckConstraints` · `sesion_uuid` sin FK dura |

**Vistas (endpoints API):**

| Endpoint | Método | Responsabilidad |
|---|---|---|
| `/api/chat/lead/` | `POST` | Validar payload · verificar `CheckConstraints` antes de impactar DB · devolver 400 si falla validación |

**Lógica:**

- `serializers.py` — Valida que llegue al menos `email` o `telefono`, que `consentimiento_rgpd` sea `true`, y que los tres campos de contexto estén presentes. Devuelve HTTP 400 si cualquier condición falla, antes de tocar la base de datos.
- Aplicar `django-ratelimit` sobre `/api/chat/lead/` por IP para mitigar spam.

**Vista Django Admin:**

- Listado de leads con filtros por `provincia`, `campo_estudio`, `colectivo` y `procesado`.
- Acción de admin para marcar leads como `procesado = True` en bloque.
- Vista de detalle con todos los datos de contacto y contexto.

---

### 4.3 App `telemetry`

Completamente independiente. Dev B puede desarrollarla en cualquier momento sin esperar a nadie.

**Modelos:**

| Modelo | Tabla | Responsabilidad |
|---|---|---|
| `ConsultaFallida` | `consulta_fallida` | Registro de fallos · campo `motivo_fallo` · flag `procesado` |
| `ContadorDemanda` | `contador_demanda` | Estadísticas agregadas anónimas · `base_conocimiento_id` sin FK dura |

**Lógica:**

- `ConsultaFallida` se inserta desde la app `rag` (Dev A) cuando el Retriever activa el fallback. Dev B define el modelo y la API de escritura; Dev A llama a esa API desde `rag`.
- `ContadorDemanda` se incrementa o crea (upsert) desde `rag` en cada consulta exitosa.
- Ambos inserts los realiza Dev A desde `rag`, pero los modelos y la lógica de escritura los define Dev B en `telemetry`.

**Vista Django Admin:**

- `ConsultaFallida`: listado filtrable por `motivo_fallo`, `provincia` y `procesado`. Acción para marcar como `procesado = True`.
- `ContadorDemanda`: listado ordenado por `total_consultas` descendente. Vista de tendencias de demanda por curso y filtro.

---

### 4.4 App `widget`

El frontend del chatbot. Vanilla JS puro, sin frameworks. Se despliega como un único archivo minificado.

**Sin modelo ni vista Django.** Nginx sirve el archivo estático directamente.

**Archivos bajo responsabilidad de Dev B:**

| Archivo | Contenido |
|---|---|
| `widget/static/chatbot.js` | Código fuente sin minificar · Shadow DOM o IIFE · máquina de estados de filtros |
| `widget/static/chatbot.css` | Estilos encapsulados · identidad visual CEFYE |
| `widget/build/chatbot.min.js` | Salida minificada lista para producción |

**Responsabilidades de implementación:**

- Botón flotante fijo en esquina inferior derecha.
- Panel desplegable colapsable con caja de texto libre y selectores opcionales de `provincia`, `campo_estudio` y `colectivo`.
- Llamada a `/api/chat/ask/` con el payload híbrido. Lectura de los flags `requiere_accion_comercial` y `fallback_activado` de la respuesta.
- Si `fallback_activado = true`: ocultar input de texto y mostrar formulario de captación de lead que llama a `/api/chat/lead/`.
- Gestión del UUID de sesión en `sessionStorage`.
- Accesibilidad: `focus trap`, atributos ARIA, navegación completa por teclado.
- Integración final: una única etiqueta `<script async>` antes del cierre de `</body>`.

---

## 5. Contratos compartidos — acordar antes de arrancar

Estas dos conversaciones son **obligatorias antes de escribir la primera línea de código**. Son los únicos puntos donde una decisión de uno bloquea al otro.

### 5.1 Contrato del payload de `/api/chat/ask/`

Dev A define la respuesta. Dev B define lo que necesita recibir como respuesta para el widget.

**Request (Dev B envía, Dev A recibe):**
```json
{
  "sesion_uuid": "uuid-v4",
  "consulta": "texto libre del usuario",
  "provincia": "Valladolid",
  "campo_estudio": "Administración",
  "colectivo": "desempleados"
}
```

**Response (Dev A devuelve, Dev B consume):**
```json
{
  "texto_respuesta": "texto generado por Ollama",
  "requiere_accion_comercial": false,
  "fallback_activado": false
}
```

> Los campos `provincia`, `campo_estudio` y `colectivo` son opcionales en el request. El backend los usa si llegan; si no, busca sin pre-filtro categórico.

### 5.2 Contrato del payload de `/api/chat/lead/`

Dev B define el endpoint. Dev B también construye el formulario del widget que lo llama.

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

**Response en éxito:**
```json
{ "ok": true }
```

**Response en error:**
```json
{ "ok": false, "errores": { "campo": "descripción del error" } }
```

### 5.3 Esquema relacional — revisión conjunta

Antes de ejecutar la primera migración, los dos revisáis juntos el documento `BBDD_Schema_CEFYE.md` y confirmáis:

- Que no hay FK entre dominios en ninguna migración.
- Que los `CheckConstraints` de `Lead` están bien definidos.
- Que el trigger de `BaseConocimiento` está en una migración `RunSQL` de `knowledge`, no en código Python.

---

## 6. Orden de entrega y dependencias

### Fase 1 — Base (semana 1, en paralelo)

| Dev A | Dev B |
|---|---|
| App `knowledge`: modelos + trigger GIN | App `sessions`: modelos + cron purga |
| Infra: `docker-compose.yml` + `.env.example` | App `telemetry`: modelos + admin |
| Reunión de revisión conjunta del esquema DB | Reunión de revisión conjunta del esquema DB |

### Fase 2 — Núcleo (semana 2, en paralelo)

| Dev A | Dev B |
|---|---|
| App `rag`: Retriever + Ollama + endpoint `ask/` | App `leads`: modelo + endpoint `lead/` + admin |
| App `ingestion`: Celery + scraping + upsert | App `widget`: estructura base + Shadow DOM + mock de `ask/` |

### Fase 3 — Integración (semana 3)

| Tarea | Responsable |
|---|---|
| Dev B sustituye el mock de `ask/` por el endpoint real de Dev A | Dev B |
| Dev A registra el cron de purga de sesiones en Docker / Celery Beat | Dev A |
| Dev A integra las escrituras en `ConsultaFallida` y `ContadorDemanda` desde `rag` | Dev A |
| Pruebas end-to-end del flujo completo: consulta → RAG → fallback → lead | Ambos |
| Minificación de `chatbot.js` → `chatbot.min.js` | Dev B |
| Configuración de Nginx para servir el widget estático | Dev A |

---

## 7. Gestión de ramas y revisiones

### Estrategia de ramas

```
main
 └── develop
      ├── feature/knowledge        (Dev A)
      ├── feature/rag              (Dev A)
      ├── feature/ingestion        (Dev A)
      ├── feature/infra            (Dev A)
      ├── feature/sessions         (Dev B)
      ├── feature/leads            (Dev B)
      ├── feature/telemetry        (Dev B)
      └── feature/widget           (Dev B)
```

- Cada app tiene su propia rama `feature/`.
- Se fusiona a `develop` mediante Pull Request con revisión del otro desarrollador.
- Nadie fusiona su propia rama: siempre revisa el otro.
- `main` solo recibe fusiones desde `develop` cuando hay una versión estable completa.

### Reglas de convivencia en el repositorio

| Regla | Motivo |
|---|---|
| Cada desarrollador solo toca los directorios de sus apps | Evita conflictos de merge |
| Las migraciones las genera el propietario de la app | Evita conflictos en el historial de migraciones |
| `settings.py` se modifica solo mediante PR revisada por ambos | Es el único archivo compartido con riesgo real de conflicto |
| Los contratos de API se documentan en este archivo antes de implementarse | Evita que uno implemente algo que el otro no puede consumir |

---

## 8. Única dependencia cross-dev y cómo desbloquearla

La única situación donde Dev B necesita algo de Dev A para avanzar es el endpoint `/api/chat/ask/` en el widget.

**Solución: mock local desde el primer día.**

Dev B crea un archivo `widget/static/mock_ask.json` con una respuesta estática que simula la respuesta real:

```json
{
  "texto_respuesta": "Hola, te puedo ayudar con información sobre nuestros cursos de administración en Valladolid. ¿Tienes alguna preferencia de horario?",
  "requiere_accion_comercial": false,
  "fallback_activado": false
}
```

En el código del widget, una variable de entorno o flag de desarrollo (`MOCK_API = true`) hace que la llamada a `ask/` devuelva este JSON en lugar de llamar al backend real. Cuando Dev A termina el endpoint, Dev B cambia el flag y el widget funciona con el backend real sin cambiar nada más.

Dev B también crea un segundo mock con `fallback_activado: true` para desarrollar y probar el flujo de captación de leads sin esperar al RAG.