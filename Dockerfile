# Imagen base ligera de Python
FROM python:3.12-slim

# Variables de entorno críticas
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar dependencias primero para aprovechar la caché de capas de Docker
COPY requirements.txt /app/

# Instalar dependencias sin guardar caché temporal para reducir el peso de la imagen
RUN pip install --no-cache-dir -r requirements.txt

# Generar el entrypoint nativamente en Linux (evita problemas de CRLF y BOM de Windows)
RUN printf '#!/bin/sh\n\
echo "Ejecutando migraciones..."\n\
python manage.py migrate --noinput\n\
echo "Creando tabla de caché para DatabaseCache..."\n\
python manage.py createcachetable\n\
echo "Iniciando servidor..."\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

# Copiar el resto del código del proyecto
COPY . /app/

# Establecer el entrypoint
ENTRYPOINT ["/entrypoint.sh"]