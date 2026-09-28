# App `leads` — Documentación técnica

## 1. Introducción

La aplicación `leads` forma parte del backend del proyecto y tiene como objetivo gestionar la **captura y almacenamiento de contactos comerciales** procedentes del sistema de chat.

El diseño de esta aplicación parte de un requisito principal:

> **Tolerancia cero a datos corruptos.**

Esto significa que no basta con validar los datos únicamente en el frontend o en la API. La aplicación incorpora diferentes niveles de protección para evitar que se almacenen registros incompletos o inconsistentes.

La aplicación implementa:

* Modelo persistente `Lead`.
* Validación mediante Django REST Framework.
* Validación adicional mediante restricciones de base de datos.
* Endpoint `POST /api/chat/lead/`.
* Protección contra spam mediante `django-ratelimit`.
* Tests automáticos para comprobar los casos de fallo obligatorio.
* Integración con Django Admin.
* Acción masiva para marcar leads como procesados.
* Relación desacoplada con las sesiones del chat mediante `sesion_uuid`.

---

# 2. Requisitos iniciales

Los requisitos definidos para la aplicación fueron los siguientes.

## 2.1. Modelo `Lead`

El modelo debe almacenar los datos de contacto y contexto:

* `nombre`
* `email`
* `telefono`
* `provincia`
* `campo_estudio`
* `colectivo`

Además, debe incluir:

* `consentimiento_rgpd`
* `sesion_uuid`
* `procesado`
* `creado_en`

También se estableció que el modelo debe tener **3 `CheckConstraint`** para reforzar la integridad de los datos directamente desde la base de datos.

## 2.2. Desacoplamiento de la sesión

El campo `sesion_uuid` debe guardar el identificador de la sesión del chat, pero **sin establecer una Foreign Key** con el modelo `Sesion`.

Por tanto, no se debe crear una relación como:

```python
sesion = models.ForeignKey(...)
```

sino almacenar únicamente el UUID:

```python
sesion_uuid = models.UUIDField(...)
```

## 2.3. API

Debe existir el endpoint:

```text
POST /api/chat/lead/
```

Este endpoint permite recibir los datos de un nuevo lead.

## 2.4. Protección contra spam

La API debe utilizar `django-ratelimit` para limitar las peticiones según la dirección IP.

## 2.5. Validación obligatoria

Antes de acceder a la base de datos, el serializer debe rechazar los siguientes casos:

1. No existe ni `email` ni `telefono`.
2. `consentimiento_rgpd` es `false`.

Ambos casos deben devolver:

```text
HTTP 400 Bad Request
```

## 2.6. Django Admin

El administrador debe poder:

* Visualizar los leads.
* Buscar leads.
* Filtrar por `provincia`.
* Filtrar por `campo_estudio`.
* Filtrar por `colectivo`.
* Filtrar por `procesado`.
* Marcar varios leads como procesados mediante una acción masiva.

---

# 3. Arquitectura general

La aplicación sigue una estructura típica de Django + Django REST Framework:

```text
leads/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
└── tests.py
```

Cada archivo tiene una responsabilidad concreta.

```text
models.py
    ↓
Define la estructura de los datos

serializers.py
    ↓
Valida los datos recibidos por la API

views.py
    ↓
Gestiona las peticiones HTTP

urls.py
    ↓
Define las rutas de la API

admin.py
    ↓
Permite gestionar los leads desde Django Admin

tests.py
    ↓
Comprueba automáticamente que las reglas funcionan
```

---

# 4. Dependencias utilizadas

La aplicación utiliza Django y Django REST Framework.

En `INSTALLED_APPS` se incluye:

```python
"rest_framework",
```

## 4.1. Motivo de utilizar Django REST Framework

Django REST Framework, también conocido como DRF, proporciona las herramientas necesarias para construir la API.

Por ejemplo, se utilizan:

```python
from rest_framework import serializers
```

y:

```python
from rest_framework import generics
```

El `ModelSerializer` permite convertir los datos recibidos mediante JSON en objetos Django y realizar su validación.

Por otro lado, `CreateAPIView` permite implementar de forma sencilla un endpoint destinado a crear nuevos registros.

---

# 5. Modelo `Lead`

El modelo representa un contacto comercial almacenado de forma persistente en la base de datos.

La estructura implementada es:

```python
import uuid

from django.db import models
from django.db.models import Q


class Lead(models.Model):
    nombre = models.CharField(max_length=150)

    email = models.EmailField(blank=True, null=True)

    telefono = models.CharField(max_length=30, blank=True, null=True)

    provincia = models.CharField(max_length=100)

    campo_estudio = models.CharField(max_length=150)

    colectivo = models.CharField(max_length=100)

    consentimiento_rgpd = models.BooleanField(default=False)

    sesion_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,
        blank=True,
    )

    procesado = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(telefono__isnull=False),
                name="lead_email_o_telefono",
            ),

            models.CheckConstraint(
                condition=Q(consentimiento_rgpd=True),
                name="lead_consentimiento_rgpd",
            ),

            models.CheckConstraint(
                condition=Q(nombre__isnull=False) & ~Q(nombre=""),
                name="lead_nombre_no_vacio",
            ),
        ]

        ordering = ["-creado_en"]

    def __str__(self):
        return self.nombre
```

---

# 6. Explicación de los campos

## 6.1. `nombre`

```python
nombre = models.CharField(max_length=150)
```

Almacena el nombre del contacto.

Se utiliza `CharField` porque se trata de texto de longitud limitada.

El límite establecido es de 150 caracteres.

---

## 6.2. `email`

```python
email = models.EmailField(
    blank=True,
    null=True
)
```

Almacena el correo electrónico.

Se utiliza `EmailField` porque Django proporciona validaciones específicas para direcciones de correo.

El campo puede estar vacío porque el requisito permite que el contacto proporcione:

* email

o:

* teléfono.

No es obligatorio disponer de ambos.

---

## 6.3. `telefono`

```python
telefono = models.CharField(
    max_length=30,
    blank=True,
    null=True
)
```

Almacena el número de teléfono.

Se utiliza `CharField` en lugar de un campo numérico porque un teléfono **no es realmente un número matemático**.

Por ejemplo, puede contener:

```text
+34 600 123 456
```

Además, no necesitamos realizar operaciones matemáticas con él.

---

# 7. `provincia`

```python
provincia = models.CharField(max_length=100)
```

Almacena la provincia asociada al lead.

Por ejemplo:

```text
León
Madrid
Valladolid
Salamanca
```

Este campo también se utiliza posteriormente en Django Admin para realizar filtros.

---

# 8. `campo_estudio`

```python
campo_estudio = models.CharField(max_length=150)
```

Indica el ámbito de estudios o formación del contacto.

Por ejemplo:

```text
Laboratorio
Informática
Administración
Sanidad
```

El campo permite posteriormente segmentar los leads desde el panel de administración.

---

# 9. `colectivo`

```python
colectivo = models.CharField(max_length=100)
```

Permite identificar el colectivo al que pertenece el contacto.

Este dato proporciona contexto adicional al lead.

También se utiliza como filtro en Django Admin.

---

# 10. `consentimiento_rgpd`

```python
consentimiento_rgpd = models.BooleanField(default=False)
```

Indica si el usuario ha aceptado el consentimiento correspondiente al tratamiento de sus datos.

Se utiliza `BooleanField` porque solamente existen dos estados:

```text
True  → consentimiento aceptado
False → consentimiento no aceptado
```

El valor por defecto es:

```python
False
```

Esto es importante desde el punto de vista de seguridad: si por algún motivo no se proporciona el consentimiento, el valor no se interpreta automáticamente como aceptado.

Además, existe una validación en el serializer y una restricción de base de datos para impedir almacenar un Lead sin consentimiento.

---

# 11. `sesion_uuid`

```python
sesion_uuid = models.UUIDField(
    default=uuid.uuid4,
    editable=False,
    null=True,
    blank=True,
)
```

Este campo identifica la sesión del chat relacionada con el lead.

El proyecto ya dispone de un modelo `Sesion`:

```python
class Sesion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    ultima_actividad = models.DateTimeField(auto_now=True)
```

Sin embargo, el requisito especifica que `Lead` no debe tener una Foreign Key hacia `Sesion`.

Por ello se decidió almacenar solamente el UUID.

---

# 12. Motivo de no utilizar Foreign Key

Una relación tradicional sería:

```python
sesion = models.ForeignKey(
    Sesion,
    on_delete=models.CASCADE
)
```

Esto crearía una relación fuerte entre ambas tablas.

Sin embargo, el requisito exige que `Lead` permanezca desacoplado.

Por eso se utiliza:

```python
sesion_uuid = models.UUIDField(...)
```

De esta forma:

```text
Sesion
  │
  │ id = UUID
  │
  └───────────────┐
                  │
                  ▼
              sesion_uuid
                 Lead
```

El Lead puede almacenar el UUID de una sesión sin que la base de datos tenga que comprobar que dicha sesión existe.

Esto permite que ambos dominios evolucionen de forma independiente.

---

# 13. `procesado`

```python
procesado = models.BooleanField(default=False)
```

Indica si el lead ya ha sido procesado por el equipo encargado de gestionarlo.

Estados:

```text
False → pendiente
True  → procesado
```

El valor inicial es `False` porque un lead recién creado todavía no ha sido gestionado.

Este campo también se utiliza como filtro en Django Admin.

---

# 14. `creado_en`

```python
creado_en = models.DateTimeField(auto_now_add=True)
```

Guarda automáticamente la fecha y hora en la que se creó el Lead.

El valor se establece una sola vez al crear el registro.

Esto permite saber cuándo llegó cada contacto.

---

# 15. Ordenación de los leads

Se ha añadido:

```python
ordering = ["-creado_en"]
```

Esto hace que los leads aparezcan por defecto desde los más recientes hasta los más antiguos.

Por tanto:

```text
Lead creado hoy
Lead creado ayer
Lead creado hace 2 días
...
```

La razón es que normalmente los leads recientes son los que requieren atención primero.

---

# 16. Los tres `CheckConstraint`

Uno de los requisitos principales era implementar tres restricciones directamente en la base de datos.

Esto proporciona una segunda capa de protección.

---

## 16.1. Primer constraint: email o teléfono

```python
models.CheckConstraint(
    condition=Q(email__isnull=False) | Q(telefono__isnull=False),
    name="lead_email_o_telefono",
)
```

La expresión:

```python
Q(email__isnull=False) | Q(telefono__isnull=False)
```

significa:

```text
email existe
        O
telefono existe
```

Por tanto, se permite:

```text
email + teléfono
```

o:

```text
email
```

o:

```text
teléfono
```

pero no:

```text
sin email
sin teléfono
```

---

# 17. Segundo constraint: consentimiento RGPD

```python
models.CheckConstraint(
    condition=Q(consentimiento_rgpd=True),
    name="lead_consentimiento_rgpd",
)
```

La base de datos solamente acepta registros cuyo consentimiento sea:

```text
True
```

Esto refuerza la validación realizada previamente en el serializer.

---

# 18. Tercer constraint: nombre no vacío

```python
models.CheckConstraint(
    condition=Q(nombre__isnull=False) & ~Q(nombre=""),
    name="lead_nombre_no_vacio",
)
```

Esta restricción garantiza que el nombre no sea `NULL` ni una cadena vacía.

Se ha elegido esta regla como tercera protección de integridad porque el nombre es un dato básico de identificación del contacto.

---

# 19. Validación mediante Serializer

El serializer se encuentra en:

```text
leads/serializers.py
```

Su función es validar y transformar los datos recibidos por la API.

Código:

```python
from rest_framework import serializers

from .models import Lead


class LeadSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lead

        fields = [
            "id",
            "nombre",
            "email",
            "telefono",
            "provincia",
            "campo_estudio",
            "colectivo",
            "consentimiento_rgpd",
            "sesion_uuid",
            "procesado",
            "creado_en",
        ]

        read_only_fields = [
            "id",
            "procesado",
            "creado_en",
        ]

    def validate(self, attrs):

        email = attrs.get("email")
        telefono = attrs.get("telefono")

        if not email and not telefono:
            raise serializers.ValidationError(
                "Debes proporcionar un email o un teléfono."
            )

        consentimiento = attrs.get("consentimiento_rgpd")

        if consentimiento is not True:
            raise serializers.ValidationError(
                "Es necesario aceptar el consentimiento RGPD."
            )

        return attrs
```

---

# 20. Motivo de utilizar un Serializer

El serializer funciona como una barrera entre los datos externos y el modelo.

El cliente puede enviar información mediante JSON:

```json
{
    "nombre": "Ana",
    "email": "ana@example.com",
    "telefono": "600123456",
    "provincia": "León",
    "campo_estudio": "Laboratorio",
    "colectivo": "Estudiante",
    "consentimiento_rgpd": true
}
```

El serializer recibe estos datos y comprueba si cumplen las reglas antes de permitir que se cree el objeto.

---

# 21. Validación de email o teléfono

La regla obligatoria es:

> Debe existir al menos un medio de contacto.

La implementación es:

```python
email = attrs.get("email")
telefono = attrs.get("telefono")

if not email and not telefono:
    raise serializers.ValidationError(
        "Debes proporcionar un email o un teléfono."
    )
```

Si ambos están vacíos:

```text
email = ""
telefono = ""
```

se genera un error de validación.

El resultado será:

```text
HTTP 400 Bad Request
```

---

# 22. Validación del consentimiento

La segunda regla obligatoria es:

> No se puede crear un Lead si `consentimiento_rgpd` es `false`.

Se implementa:

```python
if consentimiento is not True:
    raise serializers.ValidationError(
        "Es necesario aceptar el consentimiento RGPD."
    )
```

Por tanto:

```text
True  → continúa
False → HTTP 400
```

---

# 23. Concepto de "fallo rápido"

El requisito especifica que los errores deben detectarse:

> antes de tocar la base de datos.

El flujo correcto es:

```text
Petición POST
      ↓
Serializer
      ↓
Validación
      ↓
¿Datos correctos?
      │
   ┌──┴──┐
   │     │
  NO     SÍ
   │     │
   ▼     ▼
 HTTP   Guardar
  400   en BD
```

Si el serializer encuentra un error, nunca se ejecuta:

```python
serializer.save()
```

Por tanto, no se intenta crear el registro.

---

# 24. Vista de la API

La vista se encuentra en:

```text
leads/views.py
```

Código:

```python
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from rest_framework import generics

from .models import Lead
from .serializers import LeadSerializer


@method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    ),
    name="post",
)
class LeadCreateView(generics.CreateAPIView):

    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
```

---

# 25. Motivo de utilizar `CreateAPIView`

Django REST Framework proporciona diferentes vistas genéricas.

En este caso solamente necesitamos crear un Lead.

Por ello:

```python
generics.CreateAPIView
```

es apropiado para este endpoint.

La vista ya proporciona el comportamiento necesario para recibir una petición `POST`, validar el serializer y crear el objeto.

---

# 26. Funcionamiento de la petición POST

Cuando llega:

```text
POST /api/chat/lead/
```

el flujo es:

```text
1. Django recibe la petición
          ↓
2. URL identifica LeadCreateView
          ↓
3. django-ratelimit comprueba la IP
          ↓
4. Se procesa el POST
          ↓
5. LeadSerializer recibe los datos
          ↓
6. validate() ejecuta las reglas
          ↓
7. Si falla → HTTP 400
          ↓
8. Si pasa → serializer.save()
          ↓
9. Django ORM intenta guardar el Lead
          ↓
10. Base de datos comprueba los CheckConstraint
          ↓
11. Si todo es correcto → Lead creado
          ↓
12. HTTP 201 Created
```

---

# 27. Protección contra spam

Se utiliza `django-ratelimit`.

La configuración es:

```python
@method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    ),
    name="post",
)
```

La regla significa:

```text
Máximo:
5 peticiones POST
por IP
cada minuto
```

Por ejemplo:

```text
Petición 1 → permitida
Petición 2 → permitida
Petición 3 → permitida
Petición 4 → permitida
Petición 5 → permitida
Petición 6 → bloqueada
```

Esto reduce el riesgo de que un bot genere una gran cantidad de leads automáticamente.

La elección de `5/m` es una política inicial de mitigación de spam y puede ajustarse posteriormente según el comportamiento real de la aplicación.

---

# 28. URLs

La aplicación tiene su propio archivo:

```text
leads/urls.py
```

Código:

```python
from django.urls import path

from .views import LeadCreateView


urlpatterns = [
    path(
        "lead/",
        LeadCreateView.as_view(),
        name="lead-create",
    ),
]
```

La URL principal del proyecto incluye estas rutas:

```python
path(
    "api/chat/",
    include("leads.urls"),
),
```

De esta combinación:

```text
/api/chat/
```

*

```text
lead/
```

se obtiene:

```text
POST /api/chat/lead/
```

---

# 29. Django Admin

El archivo `admin.py` permite gestionar los leads desde el panel administrativo.

La implementación es:

```python
from django.contrib import admin

from .models import Lead


@admin.action(description="Marcar leads como procesados")
def marcar_como_procesados(modeladmin, request, queryset):
    queryset.update(procesado=True)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "nombre",
        "email",
        "telefono",
        "provincia",
        "campo_estudio",
        "colectivo",
        "procesado",
        "creado_en",
    ]

    list_filter = [
        "provincia",
        "campo_estudio",
        "colectivo",
        "procesado",
    ]

    search_fields = [
        "nombre",
        "email",
        "telefono",
    ]

    actions = [
        marcar_como_procesados,
    ]
```

---

# 30. `list_display`

La propiedad:

```python
list_display = [...]
```

determina qué columnas aparecen en el listado del administrador.

Se muestran:

```text
ID
Nombre
Email
Teléfono
Provincia
Campo de estudio
Colectivo
Procesado
Fecha de creación
```

Esto facilita la gestión de los contactos.

---

# 31. `list_filter`

La configuración:

```python
list_filter = [
    "provincia",
    "campo_estudio",
    "colectivo",
    "procesado",
]
```

permite filtrar los resultados.

Por ejemplo:

```text
Provincia → León
```

o:

```text
Campo de estudio → Laboratorio
```

o:

```text
Procesado → No
```

Esto permite localizar rápidamente grupos concretos de leads.

---

# 32. `search_fields`

Se ha configurado:

```python
search_fields = [
    "nombre",
    "email",
    "telefono",
]
```

Esto permite realizar búsquedas por:

* nombre;
* correo electrónico;
* teléfono.

---

# 33. Acción masiva

Se ha creado la acción:

```python
@admin.action(description="Marcar leads como procesados")
def marcar_como_procesados(modeladmin, request, queryset):
    queryset.update(procesado=True)
```

Esta acción permite seleccionar varios leads y marcarlos como procesados de una sola vez.

Por ejemplo:

```text
☑ Lead 1
☑ Lead 2
☑ Lead 3
☐ Lead 4
```

Después se ejecuta:

```text
Marcar leads como procesados
```

Los tres seleccionados pasan a:

```text
procesado = True
```

---

# 34. Motivo de utilizar `queryset.update()`

Se utiliza:

```python
queryset.update(procesado=True)
```

en lugar de guardar cada objeto individualmente.

Esto permite realizar una actualización masiva directamente en la base de datos.

Conceptualmente:

```text
3 leads seleccionados
        ↓
UPDATE masivo
        ↓
procesado = True
```

Es más apropiado para una acción administrativa masiva.

---

# 35. Tests automatizados

Debido al requisito de TDD, se han creado pruebas para verificar principalmente las reglas de validación.

Archivo:

```text
leads/tests.py
```

Se utiliza:

```python
from rest_framework.test import APITestCase
```

Esto permite simular peticiones HTTP contra la API.

---

# 36. Test: sin email ni teléfono

Se prueba el caso:

```text
email = ""
telefono = ""
```

La expectativa es:

```text
HTTP 400
```

Además, se comprueba:

```python
Lead.objects.count() == 0
```

Esto demuestra que el Lead no se ha creado.

La prueba verifica simultáneamente:

1. El endpoint rechaza los datos.
2. Se devuelve el código HTTP correcto.
3. No se crea un registro.

---

# 37. Test: consentimiento RGPD falso

También se prueba:

```python
consentimiento_rgpd = False
```

La API debe devolver:

```text
HTTP 400 Bad Request
```

Y nuevamente:

```python
Lead.objects.count() == 0
```

debe mantenerse en cero.

Esto garantiza el requisito de fallo rápido.

---

# 38. Tests de casos válidos

También se comprueban los casos donde solamente existe uno de los dos medios de contacto.

### Solo email

```text
email = "ana@example.com"
telefono = ""
```

Debe ser válido.

### Solo teléfono

```text
email = ""
telefono = "600123456"
```

También debe ser válido.

Esto es importante porque la regla no exige ambos campos.

La regla es:

```text
email OR teléfono
```

y no:

```text
email AND teléfono
```

---

# 39. Migraciones

Después de modificar `models.py`, se generan las migraciones mediante:

```bash
python manage.py makemigrations leads
```

Este comando detecta los cambios realizados en los modelos y genera un archivo de migración.

Posteriormente:

```bash
python manage.py migrate
```

aplica los cambios a la base de datos.

El proceso es:

```text
models.py
     ↓
makemigrations
     ↓
archivo de migración
     ↓
migrate
     ↓
Base de datos
```

---

# 40. Relación entre las diferentes capas de seguridad

Una de las decisiones principales de la aplicación es no depender de una única validación.

Existen varias capas:

```text
                DATOS EXTERNOS
                      ↓
              django-ratelimit
                      ↓
                  Serializer
                      ↓
               Validaciones
                      ↓
                Django ORM
                      ↓
              CheckConstraints
                      ↓
                 BASE DE DATOS
```

Cada capa tiene una responsabilidad diferente.

---

# 41. ¿Por qué validar dos veces?

El serializer proporciona una respuesta rápida y comprensible para el cliente.

Por ejemplo:

```text
HTTP 400
"Debes proporcionar un email o un teléfono."
```

Pero la base de datos también debe estar protegida.

Si por algún error de programación otro código intentara crear directamente un Lead inválido, los `CheckConstraint` impedirían que los datos inconsistentes llegasen a almacenarse.

Por tanto:

```text
Serializer
→ protección de la API

CheckConstraint
→ protección de la persistencia
```

Esta separación proporciona mayor robustez.

---

# 42. Flujo completo de creación de un Lead

El flujo completo puede representarse así:

```text
Usuario
   │
   │ completa formulario
   ▼
Frontend / Chat
   │
   │ POST JSON
   ▼
/api/chat/lead/
   │
   ▼
Rate limit
   │
   ├── demasiadas peticiones → bloqueo
   │
   ▼
LeadCreateView
   │
   ▼
LeadSerializer
   │
   ▼
validate()
   │
   ├── sin email/teléfono → HTTP 400
   │
   ├── RGPD false → HTTP 400
   │
   ▼
serializer.save()
   │
   ▼
Django ORM
   │
   ▼
CheckConstraints
   │
   ├── datos inválidos → rechazo
   │
   ▼
Base de datos
   │
   ▼
Lead creado
   │
   ▼
HTTP 201 Created
```

---

# 43. Gestión posterior del Lead

Una vez creado el Lead, aparece en Django Admin.

El administrador puede:

```text
Buscar
  ↓
Filtrar
  ↓
Revisar
  ↓
Procesar
  ↓
Marcar como procesado
```

El campo:

```python
procesado
```

permite distinguir entre:

```text
pendiente
```

y:

```text
procesado
```

---

# 44. Resumen de archivos

| Archivo          | Responsabilidad                            |
| ---------------- | ------------------------------------------ |
| `models.py`      | Define `Lead` y sus reglas de persistencia |
| `serializers.py` | Valida los datos recibidos por la API      |
| `views.py`       | Gestiona la creación de leads              |
| `urls.py`        | Define la ruta `/api/chat/lead/`           |
| `admin.py`       | Gestiona los leads desde Django Admin      |
| `tests.py`       | Comprueba automáticamente las reglas       |
| `apps.py`        | Configura la aplicación Django             |

---

# 45. Requisitos y cumplimiento

| Requisito inicial            | Implementación               |
| ---------------------------- | ---------------------------- |
| Modelo `Lead`                | `leads/models.py`            |
| `nombre`                     | `CharField`                  |
| `email`                      | `EmailField`                 |
| `telefono`                   | `CharField`                  |
| `provincia`                  | `CharField`                  |
| `campo_estudio`              | `CharField`                  |
| `colectivo`                  | `CharField`                  |
| 3 `CheckConstraint`          | `Meta.constraints`           |
| `sesion_uuid` sin FK         | `UUIDField` independiente    |
| `POST /api/chat/lead/`       | `LeadCreateView` + `urls.py` |
| Protección anti-spam         | `django-ratelimit`           |
| Rate limit por IP            | `key="ip"`                   |
| Email o teléfono obligatorio | `Serializer.validate()`      |
| RGPD obligatorio             | `Serializer.validate()`      |
| HTTP 400                     | `ValidationError`            |
| Fallo antes de BD            | Validación antes de `save()` |
| Tests TDD                    | `tests.py`                   |
| Filtro por provincia         | `list_filter`                |
| Filtro por campo de estudio  | `list_filter`                |
| Filtro por colectivo         | `list_filter`                |
| Filtro por procesado         | `list_filter`                |
| Acción masiva                | `marcar_como_procesados`     |

---

# 46. Decisiones principales de diseño

Las principales decisiones tomadas en el desarrollo son:

### 1. Utilizar Django REST Framework

Porque la aplicación necesita exponer un endpoint HTTP basado en JSON.

### 2. Utilizar `ModelSerializer`

Porque permite reutilizar la definición del modelo y centralizar la validación de los datos recibidos.

### 3. Validar antes de guardar

Para cumplir el requisito de fallo rápido y evitar operaciones innecesarias contra la base de datos.

### 4. Mantener los `CheckConstraint`

Porque la integridad de los datos no debe depender únicamente del código de la API.

### 5. Mantener `sesion_uuid` desacoplado

Porque el requisito establece expresamente que no debe existir una Foreign Key entre `Lead` y `Sesion`.

### 6. Utilizar `django-ratelimit`

Para reducir el riesgo de creación automatizada masiva de leads.

### 7. Utilizar Django Admin

Porque proporciona una interfaz administrativa sencilla para revisar, buscar, filtrar y procesar los contactos.

### 8. Utilizar una acción masiva

Porque los administradores pueden necesitar procesar varios contactos simultáneamente.

---

# 47. Conclusión

La aplicación `leads` está diseñada como un dominio persistente encargado de recibir y almacenar contactos comerciales de forma controlada.

Su arquitectura utiliza varias capas de protección:

```text
Rate limiting
      ↓
Validación del Serializer
      ↓
Django ORM
      ↓
CheckConstraints
      ↓
Base de datos
```

Esto permite cumplir el principio de **tolerancia cero a datos corruptos**.

La API impide que lleguen a la base de datos solicitudes que no proporcionen ningún medio de contacto o que no tengan consentimiento RGPD. Al mismo tiempo, las restricciones de la base de datos proporcionan una segunda barrera para proteger la integridad de la información.

El desacoplamiento de `sesion_uuid` permite relacionar conceptualmente un lead con una sesión del chat sin crear una dependencia fuerte entre ambos dominios.

Finalmente, Django Admin proporciona las herramientas necesarias para que los leads puedan ser consultados, filtrados y procesados de manera eficiente.
