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
| `campo_estudio_raw`| `CharField` | `VARCHAR(150)` | Nullable / Opcional |
| `colectivo_raw` | `CharField` | `VARCHAR(100)` | Nullable / Opcional |
| `url_origen` | `URLField` | `VARCHAR(200)` | Referencia de origen |
| `estado` | `CharField` | `VARCHAR(20)` | Estados: `pendiente`, `procesado`, `error` |

### Tabla: `BaseConocimiento` (Zona Oficial / RAG)
Almacena los registros limpios y validados consumidos por el motor de búsqueda y recuperación.

| Columna | Tipo Django | Tipo SQL | Restricciones / Notas |
| :--- | :--- | :--- | :--- |
| `id` | `BigAutoField` | `BIGSERIAL` | Primary Key |
| `titulo` | `CharField` | `VARCHAR(255)` | Indexado |
| `contenido` | `TextField` | `TEXT` | Datos normalizados |
| `provincia` | `CharField` | `VARCHAR(100)` | - |
| `campo_estudio` | `CharField` | `VARCHAR(150)` | - |
| `colectivo` | `CharField` | `VARCHAR(100)` | - |
| `url_oficial` | `URLField` | `VARCHAR(200)` | Único (`unique=True`) |
| `activo` | `BooleanField` | `BOOLEAN` | Control de visibilidad |

---

## 3. Optimizaciones de Búsqueda y Rendimiento

### Búsqueda de Texto Completo (Full-Text Search) con Índices GIN
Para evitar latencias elevadas en el motor RAG al buscar coincidencias semánticas o de palabras clave en grandes volúmenes de texto:
1. **Vector de Búsqueda (`tsvector`):** Columna gestionada a nivel de motor de base de datos que indexa los campos clave (`titulo` y `contenido`).
2. **Índice GIN (Generalized Inverted Index):** Permite consultas de texto extremadamente rápidas en PostgreSQL sin recorrer la tabla secuencialmente (`Seq Scan`).

### Triggers Nativos en PostgreSQL
La sincronización del vector de búsqueda (`tsvector`) no recae sobre la capa de aplicación (Django ORM), evitando sobrecarga de procesamiento en los hilos de Python. Se ejecuta mediante un **Trigger a nivel de SQL** que actualiza automáticamente el vector de búsqueda cada vez que se inserta o modifica un registro en `BaseConocimiento`.

---

## 4. Persistencia y Control de Concurrencia
* **Volumen Docker (`pg_data`):** Garantiza que los datos transaccionales persistan ante reinicios o actualizaciones de los contenedores de la base de datos.
* **Tabla de Caché (`django_cache_table`):** Gestiona los bloqueos y contadores distribuidos para prevenir condiciones de carrera en el límite de peticiones por minuto (`django-ratelimit`).