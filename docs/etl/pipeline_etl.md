# Pipeline ETL de Ingestión - MiniChatbot

## 1. Propósito y Arquitectura
El pipeline ETL (Extract, Transform, Load) es el subsistema encargado de procesar los registros de cursos brutos recopilados en la zona de ensayo (`StagingCursos`) y promoverlos de forma limpia, estructurada y validada hacia la base de conocimiento oficial (`BaseConocimiento`) utilizada por el motor RAG.

* **Principio de Responsabilidad Única (SRP):** Está implementado como un comando de gestión de la CLI de Django (`ejecutar_etl`). Orquesta la captura, el filtrado por huella digital (*hash*), y el volcado transaccional a producción.

---

## 2. Ciclo de Vida de los Datos y Estados
Cada registro almacenado en `StagingCursos` transita por los siguientes estados gestionados por el pipeline:

| Estado | Descripción |
| :--- | :--- |
| `pendiente` | Estado inicial del registro al ser ingresado en staging. Espera a ser procesado por el ETL. |
| `validado` | El registro fue migrado, normalizado y actualizado exitosamente en la `BaseConocimiento`. |
| `rechazado` | Ocurrió una excepción a nivel de base de datos durante el upsert atómico. El registro es aislado para revisión. |

---

## 3. Control de Duplicados e Idempotencia
Para evitar registros redundantes y asegurar la unicidad en el buffer de staging, el pipeline implementa una doble estrategia de control:

* **Control de Huella Digital (Hash SHA-256):** A nivel de `StagingCursos`, se calcula un hash único (`hash_contenido`) combinando el título y el contenido bruto para impedir duplicados físicos mediante restricciones de unicidad (`get_or_create`).
* **Upsert en Producción:** La promoción a `BaseConocimiento` utiliza el método `update_or_create` de Django ORM tomando como clave el `titulo` del curso, actualizando dinámicamente los campos asociados (`contenido`, `provincia`, `campo_estudio`, `colectivo`, `url_oficial`).

---

## 4. Modo de Ejecución

### Ejecución Manual (Desarrollo / Local)
Para procesar los registros pendientes bajo demanda desde la terminal:

```powershell
python manage.py ejecutar_etl