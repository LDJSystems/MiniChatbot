# Orquestación y Contenerización (Docker & Docker Compose) - MiniChatbot

## 1. Arquitectura de Contenedores

El despliegue de producción está orquestado mediante `docker-compose.yml`, aislando los componentes de infraestructura, persistencia, procesamiento y exposición pública. El stack se compone de 5 servicios interconectados:

* **`db`**: PostgreSQL 15 optimizado con localización en `en_US.UTF-8` y montajes de configuración de seguridad (`pg_hba.conf`).
* **`ollama`**: Servicio de inferencia LLM con versión `0.9.6`, configurado con soporte de aceleración por hardware (GPU NVIDIA) y un tiempo de vida ajustado (`OLLAMA_KEEP_ALIVE=0`).
* **`ollama-init`**: Contenedor utilitario de inicialización que asegura la descarga y disponibilidad automática del modelo especificado al arrancar el stack.
* **`web`**: Aplicación Django ejecutándose bajo Gunicorn con 3 workers concurrentes, responsable de ejecutar la recolección de estáticos y procesar las peticiones de la API.
* **`nginx`**: Proxy inverso encargado de recibir el tráfico web público y enrutarlo de forma segura hacia el servicio interno.

## 2. Aislamiento de Red

Para garantizar la seguridad de la infraestructura y minimizar la superficie de ataque, se implementa una red interna tipo bridge (`internal`):

* **Puertos Expuestos al Host/Exterior:**
  * **Puerto 80**: Único punto de entrada público expuesto al exterior, gestionado exclusivamente por Nginx.
  * *Nota de desarrollo*: Los puertos de base de datos ($5432$) y Ollama ($11434$) permanecen **estrictamente aislados** dentro de la red interna, prohibiendo el acceso directo desde fuera de los contenedores.

## 3. Persistencia y Volúmenes

Para evitar la pérdida de datos transaccionales y la redundancia de descargas pesadas en redespliegues, se definen tres volúmenes principales:

* **`pg_data`**: Almacena los ficheros de datos de PostgreSQL, garantizando la persistencia de tablas, índices GIN y la tabla de caché.
* **`ollama_models`**: Cachea los pesos del modelo LLM descargados en `/root/.ollama`, evitando re-descargas masivas de gigabytes en cada actualización del contenedor.
* **`static_volume`**: Volumen compartido entre el servicio `web` (que ejecuta `collectstatic`) y el contenedor de `nginx` para servir los archivos estáticos de forma eficiente sin sobrecargar a Gunicorn.