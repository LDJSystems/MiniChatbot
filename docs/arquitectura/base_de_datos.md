### 2. Actualización de `docs/arquitectura/base_de_datos.md`

# Arquitectura y Optimización de Base de Datos - MiniChatbot

## 1. Stack Tecnológico
* **Motor:** PostgreSQL 15 (ejecutado en contenedor aislado mediante Docker Compose con soporte de localización `en_US.UTF-8`).
* **Gestor de Caché:** `DatabaseCache` (`django_cache_table`) para persistencia y sincronización de contadores de *rate limit* entre múltiples *workers* de Gunicorn.

---

## 2. Esquema y Modelos de Datos

### Tabla: `StagingCursos` (Zona de Staging / Ingesta)
Almacena los datos brutos extraídos antes de ser procesados por el pipeline ETL.

| Columna | Tipo Django | Tipo SQL | Restricciones / Notas |
| :--- | :--- | :--- | :--- |
| `id` | `BigAutoField` | `BIGSERIAL` | Primary Key |
| `titulo_raw` | `CharField` | `VARCHAR(255)` | Texto sin procesar |
| `contenido_raw` | `TextField` | `TEXT` | Descripción cruda |
| `provincia_raw` | `CharField` | `VARCHAR(100)` | Nullable / Opcional |
| `campo_estudio_raw`| `CharField` | `VARCHAR(100)` | Nullable / Opcional |
| `colectivo_raw` | `CharField` | `VARCHAR(100)` | Nullable / Opcional |
| `url_origen` | `URLField` | `VARCHAR(200)` | Referencia de origen |
| `hash_contenido` | `CharField` | `VARCHAR(64)` | Índice único de control de duplicados (SHA-256) |
| `estado` | `CharField` | `VARCHAR(30)` | Estados: `pendiente`, `validado`, `rechazado` |
| `extraido_en` | `DateTimeField` | `TIMESTAMP` | Fecha de registro en staging |

### Tabla: `BaseConocimiento` (Zona Oficial / RAG)
Almacena los registros limpios y validados consumidos por el motor de búsqueda y recuperación.

| Columna | Tipo Django | Tipo SQL | Restricciones / Notas |
| :--- | :--- | :--- | :--- |
| `id` | `BigAutoField` | `BIGSERIAL` | Primary Key |
| `titulo` | `CharField` | `VARCHAR(255)` | Indexado (Clave de Upsert) |
| `contenido` | `TextField` | `TEXT` | Datos normalizados |
| `provincia` | `CharField` | `VARCHAR(100)` | - |
| `campo_estudio` | `CharField` | `VARCHAR(100)` | - |
| `colectivo` | `CharField` | `VARCHAR(100)` | - |
| `url_oficial` | `URLField` | `VARCHAR(200)` | Enlace oficial del recurso |
| `activo` | `BooleanField` | `BOOLEAN` | Control de visibilidad |
| `vector_busqueda` | `SearchVector` | `TSVECTOR` | Índice GIN para Full-Text Search |
| `actualizado_en` | `DateTimeField` | `TIMESTAMP` | Marca de tiempo de sincronización |

### Tablas de Operaciones y Telemetría (`operaciones`)
* **`Lead`**: Captura de contactos con restricciones estrictas de base de datos (`CheckConstraint`) para validar la presencia de al menos un canal de contacto (email o teléfono), consentimiento RGPD obligatorio y completitud de contexto geográfico/temático.
* **`ConsultaFallida`**: Registro analítico de consultas que no obtuvieron respuesta satisfactoria en el motor RAG, estructurado con un índice optimizado sobre el campo `procesado`.
* **`ContadorDemanda`**: Conteo agregado de la demanda de cursos indexado por ID de conocimiento, provincia, campo de estudio y colectivo.

---

## 3. Gobernanza y Panel de Administración (Django Admin)
Para garantizar la integridad operativa y analítica de los datos:
* **Modelos de Telemetría (`ConsultaFallida`, `ContadorDemanda`, `Lead`):** Configurados con permisos de solo lectura (`has_add_permission` restringido y campos protegidos) para evitar alteraciones manuales accidentales de las métricas.
* **Acciones Personalizadas:** Se implementaron acciones en lote (*Admin Actions*) en el administrador de `StagingCursos` y `BaseConocimiento` para la activación/inactivación y procesamiento manual directo desde la interfaz web.

---

## 4. Optimizaciones de Búsqueda y Rendimiento
* **Búsqueda de Texto Completo (Full-Text Search) con Índices GIN:** Para evitar latencias elevadas en el motor RAG al buscar coincidencias en grandes volúmenes de texto.
* **Persistencia Docker (`pg_data`):** Garantiza que los datos transaccionales persistan ante reinicios o actualizaciones de los contenedores de la base de datos.