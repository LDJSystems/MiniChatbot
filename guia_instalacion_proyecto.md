# 🛠️ Setup del Proyecto MiniChatbot

## Requisitos previos

- Python 3.12.10
- PostgreSQL 17 ([Descargar](https://www.postgresql.org/download/windows/))
- Docker Desktop ([Descargar](https://www.docker.com/products/docker-desktop/))

---

## ℹ️ Si tienes PostgreSQL 18 instalado

PostgreSQL 18 es compatible con este proyecto, pero al ser una versión aún en desarrollo puede presentar comportamientos inesperados. Puedes continuar con él, teniendo en cuenta lo siguiente:

- El puerto por defecto puede ser **5433** en lugar de 5432 — compruébalo y ajusta `DB_PORT` en el `.env` en consecuencia.
- Selecciona el locale **English, United States** durante la instalación para evitar errores de codificación con `psycopg`.
- Si encuentras errores que no aparecen en la sección de problemas frecuentes y no ocurren en PostgreSQL 17, lo más probable es que sean incompatibilidades propias de la versión beta.

**Si prefieres evitar estos riesgos**, puedes migrar a PostgreSQL 17 siguiendo estos pasos:

**1. Desinstala PostgreSQL 18**
- Panel de Control → Programas → Desinstalar `PostgreSQL 18`

**2. Elimina los datos que quedaron (la desinstalación no los borra)**

Abre PowerShell como administrador y ejecuta:
```powershell
Remove-Item -Recurse -Force "C:\Program Files\PostgreSQL"
```

**3. Instala PostgreSQL 17**
- Descarga el instalador desde [postgresql.org](https://www.postgresql.org/download/windows/) → Download the installer → versión **17.x, Windows x86-64**
- Durante la instalación:
  - Anota bien la contraseña que pongas para el usuario `postgres`
  - Puerto: **5432** (por defecto)
  - Locale: **English, United States** (importante para evitar errores de codificación)
- Cuando al final pregunte si lanzar **Stack Builder**, cancélalo, no es necesario

---

## 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd MiniChatbot
```

---

## 2. Crear el entorno virtual e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Configurar PostgreSQL

Abre PowerShell y conéctate como superusuario:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -p 5432 -h 127.0.0.1
```

Te pedirá la contraseña que pusiste durante la instalación. Una vez dentro ejecuta:

> ⚠️ Sustituye `tu_usuario` y `tu_contraseña` por los valores que quieras. Anótalos: los necesitarás en el paso 4.

```sql
CREATE USER tu_usuario WITH PASSWORD 'tu_contraseña';
CREATE DATABASE cefye_db OWNER tu_usuario;
\c cefye_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\q
```

---

## 4. Configurar las variables de entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Edita el `.env` con tus credenciales. Usa el mismo `tu_usuario` y `tu_contraseña` que pusiste en el paso 3:

```env
# ⚠️ Este SECRET_KEY es solo para desarrollo local. Nunca lo uses en producción.
SECRET_KEY=django-insecure-dev-key-local-123456789
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=cefye_db
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_HOST=127.0.0.1
DB_PORT=5432
```

---

## 5. Ejecutar las migraciones

```bash
python manage.py migrate
```

---

## 6. Levantar Ollama con Docker

En local, solo necesitas levantar el servicio de Ollama. Django corre fuera del contenedor durante el desarrollo.

```bash
docker compose up ollama -d
```

> ℹ️ `docker compose up -d` (sin especificar servicio) levanta toda la pila incluyendo nginx y la base de datos en contenedor, lo cual está pensado para producción, no para desarrollo local.

---

## 7. Crear el superusuario de Django

Necesitas una cuenta de administrador para acceder al panel de Django (`/admin`) y cargar datos en la base de conocimiento:

```bash
python manage.py createsuperuser
```

Te pedirá nombre de usuario, email (opcional) y contraseña. Anótalos.

---

## 8. Arrancar el servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en [http://localhost:8000](http://localhost:8000).
El panel de administración estará en [http://localhost:8000/admin](http://localhost:8000/admin).

---

## ❗ Problemas frecuentes

### `UnicodeDecodeError` al conectar con psycopg2
PostgreSQL está respondiendo con caracteres en español que Python no puede decodificar. Solución: reinstala PostgreSQL 17 seleccionando el locale **English, United States**.

### `data type text has no default operator class for access method "gin"`
Falta la extensión `pg_trgm`. Conéctate a `cefye_db` y ejecuta:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Error de contraseña al conectar
Verifica que el usuario que creaste en el paso 3 existe en PostgreSQL y que la contraseña en el `.env` (`DB_USER` y `DB_PASSWORD`) coincide exactamente con la que pusiste al crearlo.

### Puerto incorrecto
PostgreSQL 17 usa el puerto **5432** por defecto. Si tenías el 18 instalado antes, puede que tu `.env` tenga `DB_PORT=5433` — cámbialo a `5432`.

### psql no se reconoce como comando
PostgreSQL no está en el PATH. Usa la ruta completa:
```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -p 5432 -h 127.0.0.1
```