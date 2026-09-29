# App Telemetry

## Descripción general

La app **Telemetry** ha sido desarrollada como un módulo independiente encargado de recopilar y visualizar información estadística sobre el funcionamiento del chatbot.

Su objetivo principal es registrar:

* Consultas que no han podido ser resueltas correctamente.
* Tendencias de uso del conocimiento disponible.
* Métricas de demanda que permitan identificar qué contenidos son los más consultados.

Esta aplicación no participa directamente en la lógica de conversación, recuperación de conocimiento o gestión de sesiones. Su función es exclusivamente analítica y de monitorización.

---

# Objetivos de diseño

Durante el desarrollo se ha seguido una arquitectura desacoplada para evitar dependencias innecesarias entre aplicaciones.

La dependencia prevista es:

```text
chat
  │
  └──► telemetry

rag
  │
  └──► telemetry

conocimiento
  │
  └──► telemetry
```

La aplicación **Telemetry** no conoce la estructura interna de ninguna otra aplicación y no importa modelos externos.

Esto permite:

* Mayor mantenibilidad.
* Menor acoplamiento entre módulos.
* Facilidad para modificar otras aplicaciones sin afectar a Telemetry.
* Posibilidad de reutilizar Telemetry en otros proyectos.

---

# Modelo `ConsultaFallida`

## Finalidad

Registrar consultas que el sistema no ha podido resolver correctamente.

Permite analizar:

* Huecos en la base de conocimiento.
* Errores de recuperación de contexto.
* Fallos producidos en el backend.
* Casos que requieren revisión manual.

## Campos

### `motivo_fallo`

```python
motivo_fallo = models.TextField()
```

Describe la causa del fallo.

Ejemplos:

```text
sin_resultados
timeout_backend
sin_contexto
error_rag
```

---

### `procesado`

```python
procesado = models.BooleanField(default=False)
```

Indica si el registro ya ha sido revisado por un administrador.

---

### `creado_en`

```python
creado_en = models.DateTimeField(auto_now_add=True)
```

Fecha de creación automática del registro.

---

# Modelo `ContadorDemanda`

## Finalidad

Registrar la demanda de los elementos de conocimiento consultados por los usuarios.

La finalidad es generar estadísticas de uso.

---

## Decisión importante de diseño

El requisito del proyecto establece que:

```text
base_conocimiento_id
```

debe ser un entero simple.

Por este motivo **NO se utiliza**:

```python
ForeignKey
```

hacia la aplicación de conocimiento.

Se ha implementado:

```python
base_conocimiento_id = models.PositiveIntegerField()
```

Esto mantiene el desacoplamiento entre aplicaciones.

Telemetry únicamente almacena el identificador recibido.

---

## Campos

### `base_conocimiento_id`

```python
base_conocimiento_id = models.PositiveIntegerField()
```

Identificador del elemento de conocimiento consultado.

---

### `demanda`

```python
demanda = models.PositiveIntegerField(default=0)
```

Número de veces que dicho elemento ha sido solicitado.

---

### `actualizado_en`

```python
actualizado_en = models.DateTimeField(auto_now=True)
```

Fecha de última actualización del contador.

---

# Optimización mediante índices

Se han añadido índices para mejorar el rendimiento de las consultas.

```python
indexes = [
    models.Index(
        fields=["-demanda"],
        name="telemetry_demanda_idx",
    ),
    models.Index(
        fields=["base_conocimiento_id"],
        name="telemetry_bc_id_idx",
    ),
]
```

## Beneficios

Permiten acelerar:

* Búsquedas por identificador.
* Obtención de los contenidos más demandados.
* Consultas estadísticas futuras.

---

# Administración mediante Django Admin

Se ha implementado administración personalizada para ambos modelos.

---

## `ConsultaFallidaAdmin`

Permite:

* Visualizar fallos registrados.
* Filtrar por estado de procesamiento.
* Buscar por motivo de fallo.
* Ordenar por fecha de creación.

### Acción masiva

Se añadió una acción administrativa:

```python
Marcar consultas seleccionadas como procesadas
```

Esta acción actualiza automáticamente:

```python
procesado = True
```

en todos los registros seleccionados.

---

## `ContadorDemandaAdmin`

Permite:

* Visualizar contadores registrados.
* Buscar por identificador de conocimiento.
* Ordenar automáticamente por demanda descendente.

Configuración aplicada:

```python
ordering = ["-demanda"]
```

---

# Pruebas realizadas

## Migraciones

Se realizó la generación y aplicación de las migraciones mediante:

```shell
python manage.py makemigrations
python manage.py migrate
```

### Resultado

```text
Todas las migraciones aplicadas correctamente.
```

---

## Creación de consultas fallidas

Pruebas realizadas:

```python
ConsultaFallida.objects.create(
    motivo_fallo="sin_resultados"
)
```

```python
ConsultaFallida.objects.create(
    motivo_fallo="timeout_backend"
)
```

### Resultado

```text
Registros creados correctamente.
```

---

## Creación de contadores de demanda

Prueba realizada:

```python
ContadorDemanda.objects.create(
    base_conocimiento_id=10,
    demanda=25
)
```

### Resultado

```text
Contador almacenado correctamente.
```

---

## Ordenación por demanda

Verificación:

```python
ContadorDemanda.objects.all()
```

### Resultado esperado

```text
Mayor demanda
      ↓
Menor demanda
```

Cumpliendo el requisito:

```text
Visualización de tendencias ordenadas por demanda descendente.
```

---

# Estado actual

## Implementado

* Modelo `ConsultaFallida`.
* Modelo `ContadorDemanda`.
* Índices de rendimiento.
* Administración personalizada.
* Acción bulk para procesar fallos.
* Ordenación por demanda descendente.
* Migraciones verificadas.
* Arquitectura desacoplada.

## Pendiente como mejora futura

* Dashboard de tendencias.
* Gráficos de demanda.
* Exportación de métricas.
* Servicios de registro centralizados (`services.py`).
* API para consumo externo de métricas.

---

# Conclusión

La aplicación **Telemetry** ha sido implementada como un módulo independiente de monitorización y análisis.

Cumple los requisitos funcionales definidos para el proyecto, mantiene un bajo nivel de acoplamiento con el resto de aplicaciones y queda preparada para futuras ampliaciones orientadas a la explotación de métricas y tendencias de uso del chatbot.
