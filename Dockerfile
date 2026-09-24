# Imagen base ligera de Python
FROM python:3.12-slim

# Variables de entorno críticas
# Evita la creación de archivos .pyc innecesarios
ENV PYTHONDONTWRITEBYTECODE=1
# Fuerza el volcado directo de los logs de Django (stdout/stderr) sin buffer
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar dependencias primero para aprovechar la caché de capas de Docker
COPY requirements.txt /app/

# Instalar dependencias sin guardar caché temporal para reducir el peso de la imagen
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . /app/