# Pipeline ETL de Ingestión - MiniChatbot

## 1. Propósito y Arquitectura
El pipeline ETL (Extract, Transform, Load) es el subsistema encargado de procesar los registros de cursos brutos recopilados en la zona de ensayo (`StagingCursos`) y promoverlos de forma limpia, estructurada y validada hacia la base de conocimiento oficial (`BaseConocimiento`) utilizada por el motor RAG.

* **Principio de Responsabilidad Única (SRP):** Está implementado de forma exclusiva como un comando de gestión de la CLI de Django (`procesar_staging`). Carece de vistas, serializadores o rutas HTTP, operando estrictamente como una tarea de procesamiento por lotes (*batch processing*).

---

## 2. Ciclo de Vida de los Datos y Estados
Cada registro almacenado en `StagingCursos` transita por los siguientes estados gestionados por el pipeline:

| Estado | Descripción |
| :--- | :--- |
| `pendiente` | Estado inicial del registro al ser ingresado en staging. Espera a ser procesado por el ETL. |
| `procesado` | El registro fue migrado y actualizado exitosamente en la `BaseConocimiento`. |
| `error` | Ocurrió una excepción durante la transformación o carga. El registro es aislado para revisión. |

---

## 3. Control de Duplicados e Idempotencia
Para evitar registros redundantes en la base de conocimiento del chatbot, el pipeline utiliza una estrategia de *upsert* basada en el método `update_or_create` de Django ORM:

* **Clave de Unicidad:** La coincidencia se evalúa mediante la `url_oficial` (o URL de origen).
* **Comportamiento:**
  * Si la URL ya existe en `BaseConocimiento`, el registro se **actualiza** con los últimos datos normalizados provenientes de staging.
  * Si la URL no existe, se **crea** un nuevo registro activo.

---

## 4. Modo de Ejecución

### Ejecución Manual (Desarrollo / Local)
Para procesar los registros pendientes bajo demanda desde la terminal:

```powershell
python manage.py procesar_staging
```

### Ejecución en Producción (Docker)
Dado que el contenedor de la aplicación corre dentro de un entorno aislado con Gunicorn, la ejecución se realiza invocando el comando directamente en el contenedor web activo:

```bash
docker compose exec web python manage.py procesar_staging
```

### Automatización Sugerida (Producción)
Para mantener la base de conocimiento sincronizada de forma autónoma, se recomienda programar la ejecución periódica del comando mediante un trabajo automatizado (`cron` en el sistema host o un contenedor dedicado de tareas programadas):

```bash
0 */4 * * * cd /ruta/al/proyecto && docker compose exec -T web python manage.py procesar_staging >> /var/log/etl_cursos.log 2>&1
```