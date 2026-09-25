# Aplicación de Ingestión (`ingestion`) - Documentación Técnica

## 1. Propósito
Módulo dedicado exclusivamente a la extracción, recolección y volcado inicial de datos brutos desde fuentes externas (scraping, APIs o fuentes de terceros) hacia la capa de ensayo (*Staging*).

---

## 2. Decisiones de Arquitectura: Ausencia de Modelos y Vistas

La aplicación `ingestion` está diseñada de forma minimalista, conteniendo únicamente comandos de gestión (`management/commands/`), desacoplada por completo de la capa web y de la persistencia oficial por los siguientes motivos técnicos:

* **Principio de Responsabilidad Única (SRP):** La ingesta de datos externos es un proceso de procesamiento por lotes (*batch processing*). Mezclar la lógica de extracción con entidades del dominio violaría la separación de incumbencias. Los datos recolectados se mapean directamente sobre la tabla `StagingCursos` (perteneciente a la app `conocimiento`).
* **Inexistencia de Capa HTTP:** Al no interactuar directamente con clientes web, se eliminan por completo controladores (`views.py`), serializadores y enrutamiento (`urls.py`).
* **Ejecución Exclusiva por Línea de Comandos (CLI):** Toda la lógica opera mediante clases derivadas de `BaseCommand`, facilitando su ejecución programada en segundo plano o mediante contenedores dedicados sin sobrecargar el flujo HTTP del proyecto.