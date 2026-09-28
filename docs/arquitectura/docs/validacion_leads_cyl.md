# Documentación Técnica: Validación Geográfica de Leads (Castilla y León)

## Resumen del Problema
El sistema permitía registrar leads con provincias fuera de Castilla y León y presentaba colisiones de rutas en el enrutador principal debido al orden de evaluación de los prefijos `/api/chat/`. Además, existían errores de dependencias en las migraciones que impedían la correcta ejecución de las pruebas unitarias.

## Solución Implementada
1. **Modelo y Población**: Creación y poblamiento automatizado de las provincias oficiales de Castilla y León mediante migración de datos (`0004_poblar_provincias_cyl.py`).
2. **Serialización y Validación**: Implementación de `validate_provincia` en `LeadSerializer` para verificar contra la base de datos que el valor pertenezca estrictamente a CyL.
3. **Enrutamiento (`config/urls.py`)**: Reordenamiento de las inclusiones de URLs para priorizar `operaciones.urls` frente a las rutas genéricas de chat.
4. **Pruebas Unitarias (`operaciones/tests.py`)**: Cobertura completa con `pytest` validando registros exitosos en CyL y rechazos por provincias inválidas o falta de consentimiento RGPD.

## Verificación
Ejecutar el siguiente comando para correr la suite de pruebas:
```powershell
pytest operaciones/tests.py