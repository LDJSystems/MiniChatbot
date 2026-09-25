# Proxy Inverso y Gestión de Estáticos (Nginx) - MiniChatbot

## 1. Propósito y Arquitectura

Nginx opera como el servidor web de borde (*edge server*) y proxy inverso del sistema. Sus funciones principales son:
* Terminar y gestionar las conexiones HTTP entrantes.
* Actuar como escudo protector aislando los procesos internos de Django/Gunicorn.
* Servir los archivos estáticos del proyecto de forma directa y de alto rendimiento mediante el acceso al disco compartido (`static_volume`).

## 2. Configuración del Servidor (`nginx.conf`)

La estructura de enrutamiento implementada en el proxy inverso se define de la siguiente manera:

```nginx
upstream django_web {
    server web:8000;
}

server {
    listen 80;
    server_name localhost;

    client_max_body_size 20M;

    # Gestión eficiente de archivos estáticos recolectados
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Enrutamiento de peticiones dinámicas hacia Gunicorn
    location / {
        proxy_pass http://django_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts robustos para respuestas de IA (RAG)
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

## 3. Optimizaciones Clave
* **Límite de Carga (`client_max_body_size 20M`)**: Permite la recepción segura de payloads grandes (como documentos o consultas extensas procesadas por el chatbot).
* **Timeouts Extendidos**: Los tiempos de espera de lectura y conexión (`proxy_read_timeout`) se amplían a 120 segundos para evitar cortes prematuros de conexión mientras el modelo LLM genera la respuesta RAG.