# Aplicación de Conocimiento (`conocimiento`) - Documentación Técnica

## 1. Propósito
Módulo responsable de la administración de modelos transaccionales de datos y la ejecución de procesos ETL para la actualización de la base de conocimiento del chatbot.

---

## 2. Modelos de Datos

### `StagingCursos`
* **Propósito:** Tabla de ensayo temporal (*Staging*). Almacena los registros brutos extraídos antes de ser validados y normalizados.
* **Campos Clave:** `titulo_raw`, `contenido_raw`, `url_origen`, y un campo de control `estado` (`pendiente`, `procesado`, `error`).

### `BaseConocimiento`
* **Propósito:** Repositorio oficial y definitivo consumido por el motor RAG.
* **Campos Clave:** `titulo`, `contenido`, `provincia`, `campo_estudio`, `colectivo`, `url_oficial` (única) y `activo`.

---

## 3. Pipeline ETL (`management/commands/procesar_staging.py`)
* **Ejecución:** Comando CLI (`python manage.py procesar_staging`).
* **Lógica de Procesamiento:**
  * Filtra registros en estado `pendiente`.
  * Aplica un control estricto de duplicados mediante `update_or_create` basado en la `url_oficial`.
  * Actualiza los estados de cada ítem a `procesado` o `error` según el resultado de la transacción.