# Registro de Decisiones de Arquitectura (ADR) - MiniChatbot

## ADR 1: Uso de PostgreSQL con Índices GIN y Triggers Nativos para Búsqueda
* **Contexto**: Requerimiento de búsqueda de texto eficiente dentro de la base de conocimiento del chatbot.
* **Decisión**: Utilizar PostgreSQL con columnas de búsqueda de texto optimizadas mediante índices GIN y sincronizadas de forma automática mediante triggers a nivel de motor de base de datos.
* **Consecuencias**: Se descarta la sobreingeniería de motores de búsqueda externos (Elasticsearch) o bases de datos vectoriales dedicadas, manteniendo el stack transaccional unificado y con rendimiento nativo.

## ADR 2: Implementación de `DatabaseCache` para Control de Concurrencia
* **Contexto**: El uso de `django-ratelimit` con múltiples procesos (*workers*) de Gunicorn provocaba contadores aislados en memoria al usar el backend por defecto (`LocMemCache`), anulando el límite real de peticiones por minuto.
* **Decisión**: Configurar `DatabaseCache` utilizando la base de datos PostgreSQL existente.
* **Consecuencias**: Sincronización robusta de límites de tasa entre múltiples *workers* de producción sin la complejidad operacional ni el costo de infraestructura de desplegar y mantener una instancia de Redis exclusiva para caché.

## ADR 3: Aislamiento de Red y Proxy Inverso con Nginx en Docker
* **Contexto**: Riesgo de seguridad por exposición directa de los puertos internos del motor de base de datos ($5432$) y del servidor LLM ($11434$) al exterior.
* **Decisión**: Orquestación mediante Docker Compose utilizando una red interna aislada (`internal`). Exposición exclusiva de los puertos públicos ($80$) gestionados por Nginx actuando como proxy inverso.
* **Consecuencias**: Reducción drástica de la superficie de ataque, aislamiento estricto de servicios persistentes y gestión eficiente del servicio de archivos estáticos.

## ADR 4: Desacoplamiento del Pipeline ETL como Comando CLI
* **Contexto**: Necesidad de migrar y sincronizar registros desde la tabla de ensayo (`StagingCursos`) hacia la base oficial (`BaseConocimiento`) aplicando control estricto de duplicados mediante `update_or_create`.
* **Decisión**: Implementar la lógica como un comando de gestión de Django (`procesar_staging`) totalmente independiente de vistas, serializadores o modelos HTTP.
* **Consecuencias**: Aplicación estricta del Principio de Responsabilidad Única (SRP). Facilita su ejecución automatizada por lotes (mediante tareas programadas o cron) sin contaminar la API web.