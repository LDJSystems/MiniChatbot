# Aplicación RAG (`rag`) - Documentación Técnica

## 1. Propósito
Módulo central encargado de la Recuperación y Generación Aumentada (RAG). Orquesta la búsqueda de contexto relevante en la base de datos y la interacción con el modelo de lenguaje local (Ollama) para formular respuestas fundamentadas.

---

## 2. Componentes Principales

### `retriever.py`
* **Función:** Ejecuta consultas de búsqueda de texto completo (`Full-Text Search`) optimizadas contra la tabla `BaseConocimiento` utilizando los índices GIN y operadores de PostgreSQL.
* **Mecanismo:** Filtra registros activos y asigna relevancia basada en vectores de texto (`tsvector`), retornando los fragmentos más idóneos para alimentar al generador.

### `generator.py`
* **Función:** Se comunica con la API de Ollama mediante peticiones HTTP seguras.
* **Seguridad (Prompt Injection):** Implementa delimitadores estrictos de datos para aislar el contexto recuperado de las instrucciones del sistema, neutralizando intentos de inyección de comandos o manipulación del LLM.
* **Control de Errores y Fallback:** Gestiona excepciones de conectividad o tiempos de espera (`timeout`) con el contenedor de Ollama, activando respuestas de respaldo controladas cuando el servicio no está disponible.

---

## 3. Pruebas Unitarias (`rag/tests.py`)
* **Validación:** Cobertura de pruebas mediante `pytest` y mocks de peticiones HTTP.
* **Requisitos:** Requiere el uso del decorador `@pytest.mark.django_db` para validar interacciones que utilicen caché basada en base de datos (`DatabaseCache`).