# Separación Arquitectónica: `rag` vs `operaciones`

## Contexto y Decisión de Diseño
El sistema divide su núcleo backend en dos aplicaciones Django independientes (`rag` y `operaciones`) en lugar de agruparlas en una única unidad monolítica o tratar a `rag` como un submódulo interno. Esta separación responde a una estrategia de **Contextos Delimitados (Bounded Contexts)** dentro del dominio del negocio.

---

## Desglose de Responsabilidades

### 1. Aplicación `operaciones`
* **Dominio**: Lógica transaccional, flujos de conversión de usuarios y cumplimiento legal.
* **Componentes clave**: Gestión de leads, validación estricta de provincias de Castilla y León frente a base de datos normalizada, validación de consentimiento RGPD, constraints SQL a nivel de base de datos y contadores de demanda.
* **Naturaleza**: Altamente relacional, transaccional y sujeta a reglas de negocio y restricciones de integridad estrictas.

### 2. Aplicación `rag`
* **Dominio**: Pipeline de Inteligencia Artificial, recuperación de información y generación de lenguaje natural.
* **Componentes clave**: Tubería de recuperación (*retriever*), generación (*generator*), gestión de embeddings, consultas vectoriales e integración con proveedores de modelos de lenguaje.
* **Naturaleza**: Infraestructura computacional, orientada a servicios externos e inferencia, independiente de los flujos transaccionales del cliente.

---

## ¿Por qué esta separación y no sobrefragmentación?

* **Principio de Responsabilidad Única (SoC)**: Mezclar la lógica de persistencia de leads y validación geográfica con la lógica de indexación vectorial y llamadas a LLMs violaría el acoplamiento cohesivo. Cambios en los proveedores de IA o en los umbrales de búsqueda vectorial no deben impactar el ciclo de vida transaccional del lead.
* **Aislamiento en Pruebas Unitarias (`pytest`)**: Permite ejecutar pruebas de validación de negocio (`operaciones`) sin necesidad de simular motores de embeddings o llamadas a APIs de generación de texto pesadas, optimizando el tiempo de ejecución de la suite de pruebas.
* **Escalabilidad y Mantenimiento**: Permite escalar o refactorizar de forma independiente los componentes de IA (`rag`) frente al núcleo de conversión comercial (`operaciones`).

## Flujo de Comunicación entre Apps

Las aplicaciones `rag` y `operaciones` no se comunican mediante importaciones directas de lógica de negocio o llamadas internas en Python, evitando dependencias circulares y acoplamiento rígido. Su interacción se estructura de la siguiente manera:

1. **Independencia de Endpoints (`config/urls.py`)**:
   * Cada app expone su propia interfaz HTTP bajo prefijos delimitados (ej. `/api/chat/` para la tubería de IA en `rag` y `/api/lead/` para la persistencia transaccional en `operaciones`).

2. **Orquestación mediante el Cliente (Frontend)**:
   * Es el cliente o la capa de presentación la que coordina el flujo de usuario. Por ejemplo: una consulta conversacional fluye hacia la API de `rag` para obtener la respuesta generada; si el usuario completa su intención de registro, el cliente invoca de manera independiente el endpoint de `operaciones` (`/api/lead/`) enviando los datos para su validación geográfica (Castilla y León) y de consentimiento RGPD.

3. **Persistencia Compartida a Nivel de Base de Datos**:
   * Comparten el mismo motor de base de datos relacional (PostgreSQL), lo que permite que entidades transversales o contadores de demanda accedan a las mismas tablas sin necesidad de comunicarse mediante servicios web internos (RPC).