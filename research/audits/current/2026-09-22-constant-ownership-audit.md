# Informe de barrido de constantes

**Fecha:** 2026-09-22
**Repositorio:** `symbiont-lab`
**head:** `df4eb45b370dbdd8d1676b80c6c167bc0cfe89ed`
**Estado:** diagnóstico completado; no se han aplicado cambios funcionales ni se ha ejecutado la suite de tests.

## 1. Alcance y método

Se revisó el checkout actual de:

`/home/alessbarb/workspace/repos/incubating/symbiont-lab`

Estado del repositorio al inicio:

- Rama: `main`.
- Sin cambios locales pendientes.
- `main` alineada con `origin/main`.
- No se modificaron archivos durante la revisión.
- Se revisaron `src/symbiont`, `src/symbiont_lab`, `observatory`, `scripts`, contratos JSON y módulos JavaScript.
- Se utilizó el grafo del repositorio como primera aproximación y después un inventario AST/grep de asignaciones constantes.

El inventario detectó aproximadamente:

- **259 módulos Python de producción** con constantes o asignaciones constantes.
- **804 asignaciones constantes o privadas** detectadas en `src`.
- **27 asignaciones constantes** en Observatory.

El objetivo no es mover todas las constantes a un único archivo. Eso introduciría acoplamiento y una configuración global difícil de gobernar. La regla recomendada es:

> Centralizar únicamente los valores que representan la misma invariante compartida por varios módulos. Mantener local aquello que describe el algoritmo, el formato privado, una interfaz, un protocolo independiente o un experimento concreto.

## 2. Conclusión ejecutiva

La arquitectura actual ya tiene una separación razonable entre varias clases de constantes:

- `KernelLimits`: límites duros del grafo cognitivo.
- `OrganismLimits`: límites físicos, somáticos, de recursos y seguridad.
- `PhysiologyConfig`: dinámica fisiológica y temporal.
- `EpistemicConventions`: clases, recencia, suavizado y umbrales epistemológicos.
- `runtime_defaults.py`: valores operativos del residente.
- `observatory/config.py`: configuración propia del aparato Observatory.
- Constantes locales de estudios, simulaciones, física 3D y rendering.

Por tanto, **no se recomienda crear un `constants.py` global** ni trasladar masivamente las constantes de los módulos.

Las zonas que requieren atención son:

### Prioridad alta

1. **Límites del body schema duplicados entre Python y JavaScript**:
   - `src/symbiont/core/body_schema.py`
   - `observatory/config.py`
   - `observatory/projection/body-schema.js`
   - `observatory/projection/self-schema.js`

   Existe riesgo de divergencia entre el límite real del organismo y el límite que aplica Observatory.

2. **Contrato JavaScript del body schema repartido entre varios módulos**:
   - `body-schema.js`
   - `self-schema.js`

   Hay claves, relaciones, límites y clases discretas que se repiten. Deberían compartir una fuente de contrato dentro de Observatory, sin importar nada desde `symbiont`.

3. **Límites locales expresados como literales inline**:
   - `modeling.telemetry`;
   - `modeling.culture`;
   - `modeling.runtime`;
   - algunas validaciones de `registry`, `authority` y otros módulos.

   No requieren moverse a una configuración global, pero sí convertirse en constantes nombradas del propio módulo o en campos de configuración del componente.

### Prioridad media

4. **Schema versions**:
   - En general están bien localizadas.
   - No deben fusionarse en una versión global.
   - Sí conviene corregir los pocos lugares donde aparece `schema_version: 1` inline en vez de reutilizar la constante del módulo.

5. **Límites de Observatory**:
   - `adapter.py` y `config.py` ya comparten parte de los límites.
   - Conviene establecer una única fuente dentro de Observatory para los límites del contrato de ingesta.

### Mantener como están

- Estados y enums.
- Constantes de estudios científicos.
- Seeds y escenarios experimentales.
- Geometría y materiales de física 3D.
- Claves privadas de serialización.
- Regex y namespaces locales.
- Umbrales específicos de un algoritmo.
- Defaults operativos de runtime separados de los límites biológicos.
- `KernelLimits`, `OrganismLimits`, `PhysiologyConfig` y `EpistemicConventions` como familias separadas.

## 3. Modelo de clasificación

### 3.1. Debe centralizarse

Cuando se cumplen todas o casi todas estas condiciones:

- El valor representa una única regla semántica.
- Lo consumen varios módulos.
- Si cambia en un sitio debe cambiar en todos.
- El cambio no depende del algoritmo concreto.
- La centralización no rompe los límites entre paquetes.

Ejemplos:

- límites globales de recursos del organismo;
- clases epistemológicas;
- defaults operativos del residente;
- versiones de un contrato usado por varios consumidores del mismo paquete.

### 3.2. Debe mantenerse en su módulo

Cuando el valor es:

- privado del algoritmo;
- parte de una simulación o estudio;
- una constante de rendering;
- una clave de wire format local;
- un schema version de un objeto concreto;
- un valor que puede cambiar independientemente de otros valores parecidos;
- un límite defensivo de un consumidor distinto.

### 3.3. Debe centralizarse solo dentro de un subdominio

Es el caso más frecuente en este repositorio.

Ejemplos:

- límites del contrato de Observatory;
- constantes del body schema;
- parámetros de un estudio;
- configuración de física 3D;
- límites de telemetría;
- límites del sistema de símbolos.

No debe subir a `core/limits.py` si no representa una capacidad común del organismo.

## 4. Hallazgos detallados

### 4.1. `OrganismLimits`

**Ubicación:** `src/symbiont/core/limits.py`

**Decisión:** **mantener y reforzar su papel de fuente canónica.**

No moverlo a `runtime_defaults.py`, `physiology_config.py`, `cognition/limits.py` ni `observatory/config.py`.

`OrganismLimits` describe capacidad física, de memoria, almacenamiento o seguridad del organismo. No describe cómo madura, cuándo decae, cómo aprende, cómo clasifica evidencia, cómo se renderiza ni cómo Observatory protege su entrada.

Incluye correctamente límites de:

- bytes de checkpoint;
- conocimiento e intercambio;
- partes sensoriales y regiones cognitivas;
- dependencias y evidencias;
- candidatos de coactividad;
- canales cognitivos;
- capacidades host;
- relaciones y contextos;
- perfiles, claims y trials de signal knowledge;
- colas de degradación;
- herencia y cultura.

Varios módulos crean su propia instancia:

```python
_DEFAULT_LIMITS = OrganismLimits()
```

Esto no es funcionalmente incorrecto porque la clase es inmutable, pero conviene documentar que cada instancia es una proyección de la fuente canónica y no una nueva fuente de verdad.

No se recomienda crear ahora un `DEFAULT_ORGANISM_LIMITS` global salvo que se quiera imponer identidad de instancia. El beneficio práctico sería reducido.

### 4.2. `KernelLimits`

**Ubicación:** `src/symbiont/cognition/limits.py`

**Decisión:** **mantener separado de `OrganismLimits`.**

Describe límites del grafo cognitivo: nodos, conceptos, edges, edges tentativos, mutaciones, consolidación, candidatos de consolidación, trazas de eventos, peso máximo consolidado y reaclimatación cognitiva.

Estos límites pertenecen al kernel cognitivo y ya se pasan explícitamente a nacimiento, grafo, genome, checkpoint, consolidación, runtime y bridge cognitivo.

Que algunos valores coincidan numéricamente con `OrganismLimits` no significa que representen la misma política.

### 4.3. `PhysiologyConfig`

**Ubicación:** `src/symbiont/core/physiology_config.py`

**Decisión:** **mantener centralizada dentro de fisiología.**

Incluye ratios de estados metabólicos, reparación, fatiga, temperatura, actividad, modo seguro, aging, waste, crecimiento, senescencia, reproducción y agencia prospectiva constitucional.

Esta configuración responde a cuándo cambia el organismo, a qué velocidad cambia y qué estado fisiológico adopta. No debe trasladarse a `OrganismLimits`, `EpistemicConventions` ni `runtime_defaults.py`.

Las validaciones inline como `<= 32`, `<= 64` y `<= 1.0` no necesitan convertirse en constantes globales. Solo convendría nombrarlas si se repiten en varios campos o forman parte de una política pública compartida.

### 4.4. `EpistemicConventions`

**Ubicación:** `src/symbiont/core/epistemic.py`

**Decisión:** **mantener como autoridad para convenciones epistemológicas.**

Centraliza correctamente `established_signal_min_samples`, `ewma_alpha`, el número de clases de salud, confianza, coste, madurez y actividad, además de los thresholds de recencia, madurez y ticks representativos de recencia.

Se consume desde activación cognitiva, self model, body schema, consolidación, host acclimation, host rhythms, baseline consolidado y fingerprint.

No deben trasladarse aquí los umbrales que solo pertenecen al algoritmo `BodySchemaEngine`, como soporte mínimo de regiones, soporte de dependencias, intervalo de reestructuración o caps de evidencia.

### 4.5. Body schema: principal problema de duplicación

**Fuentes actuales:**

Python:

- `src/symbiont/core/limits.py`;
- `src/symbiont/core/body_schema.py`.

Observatory Python:

- `observatory/config.py`;
- `observatory/adapter.py`.

Observatory JavaScript:

- `observatory/projection/body-schema.js`;
- `observatory/projection/self-schema.js`.

**Valores conceptualmente compartidos:**

- máximo de partes sensoriales: `256`;
- máximo de regiones cognitivas: `32`;
- máximo total de partes: `288`;
- máximo de dependencias: `256`;
- clases discretas de recencia;
- relaciones `co_acts_with` y `precedes`;
- formatos `part.sense.<32 hex>` y `part.region.<32 hex>`;
- versiones y claves del body schema.

**Decisión:** **centralizar dentro del subdominio del contrato de Observatory, pero no importar desde `symbiont`.**

La separación de Observatory respecto a `symbiont` es correcta y debe mantenerse. Observatory es un aparato pasivo que conoce sus propios contratos. Si importase `OrganismLimits` o `body_schema.py`, se rompería la frontera entre productor, adaptador y aparato de observación.

**Recomendación:** crear una fuente local de contrato dentro de Observatory, por ejemplo:

```text
observatory/projection/body-contract.js
```

o:

```text
observatory/schemas/body_limits.json
```

Debe contener únicamente límites del body schema visibles en el contrato, relaciones, versiones de wire, límites de clases y patrones de identificadores.

Después, `body-schema.js` y `self-schema.js` deben reutilizarla. El código Python de Observatory debe tener una definición equivalente verificable mediante tests.

El flujo correcto debe seguir siendo:

```text
organismo -> snapshot contractual -> Observatory
```

No:

```text
Observatory -> límites internos del organismo
```

### 4.6. `observatory/config.py`

**Decisión:** **mantener dentro de Observatory y delimitar mejor su contenido.**

Los defaults del servidor y los límites defensivos de ingesta pertenecen al aparato de observación: dirección y puerto, polling, heartbeat, protección frente a replay o ingesta descontrolada y límites de entrada.

Aunque algunos números coincidan con los del organismo, la función es diferente:

- `OrganismLimits.max_sensory_parts`: capacidad del organismo.
- `INGESTION_MAX_SENSORY_PARTS`: máximo que Observatory acepta de una entrada.

Pueden ser iguales hoy y divergir mañana legítimamente.

Como mejora futura se podrían separar:

```text
observatory/config.py
observatory/contract_limits.py
```

No es obligatorio hacerlo inmediatamente.

### 4.7. Defaults del residente

**Ubicación:** `src/symbiont/core/runtime_defaults.py`

**Decisión:** **mantener en su módulo.**

Incluye `DEFAULT_STATE_FILE`, `DEFAULT_TICK_INTERVAL_SECONDS` y `DEFAULT_CHECKPOINT_TICKS`.

Son defaults de ejecución transparente, no límites físicos, parámetros de fisiología, configuración de estudios ni configuración de Observatory.

### 4.8. Schema versions

**Decisión:** **mantener cada versión junto al contrato que versiona.**

No se recomienda crear un `GLOBAL_SCHEMA_VERSION`. Cada versión representa una evolución diferente: body schema, fingerprint, capsule, host checkpoint, signal knowledge, telemetry, physics 3D, world persistence, snapshot de Observatory, etc.

Sí conviene eliminar los casos donde aparece:

```python
"schema_version": 1
```

cuando el módulo ya dispone de una constante como `SCHEMA_VERSION`.

La regla recomendada es:

- versión privada de una clase: constante de clase;
- versión pública de un módulo: constante de módulo;
- versiones históricas aceptadas: tuple o estructura explícita en el mismo módulo.

## 5. Constantes que deben mantenerse locales

### 5.1. Enums y estados

Estados fisiológicos, lifecycle, metabolismo, agencia, hipótesis, modos de acceso, tipos de capacidad, operaciones culturales y tipos de transducción deben permanecer en sus dominios.

No son configuración. Son vocabulario del dominio y deben permanecer cerca de sus validaciones, serializadores, transiciones y tests.

### 5.2. Estudios científicos

Debe mantenerse local a cada estudio o protocolo:

- `SEEDS`;
- `CONDITIONS`;
- `THRESHOLD`;
- `AGENCY_THRESHOLD`;
- `MAX_FALSE_POSITIVE_RATE`;
- `MIN_TRUE_POSITIVE_RATE`;
- métricas de ruido, herencia y comunicación;
- tamaños de vocabulario, estados y presiones.

Estos valores forman parte del diseño experimental. No describen el runtime y no deben alimentar las decisiones del organismo.

### 5.3. Seeds y parámetros de simulación

Deben mantenerse en el estudio, campaña o world adapter. Centralizar seeds globalmente aumentaría el riesgo de compartir accidentalmente secuencias entre experimentos.

### 5.4. Física 3D

Las tolerancias del solver, límites mecánicos, iteraciones físicas, masas, segmentos, topología, materiales, ejes y articulaciones deben mantenerse en `physics3d`.

Son parámetros de un aparato físico específico y no deben trasladarse a `OrganismLimits`, `PhysiologyConfig`, runtime general ni Observatory.

### 5.5. Rendering y UI

Los límites de muestras visibles, posiciones SVG, colores, rangos de morphology, límites de gráficas y ventanas temporales deben mantenerse en los módulos de UI/rendering.

Son límites de presentación, no límites científicos ni operativos.

## 6. Literales inline que conviene nombrar

Estos valores no deben moverse necesariamente a un archivo común, pero deberían dejar de aparecer repetidos como literales.

### 6.1. `modeling/telemetry.py`

Existe un límite inline para `max_events_per_tick: int = 256`, junto a otros límites ya nombrados.

Recomendación:

```python
MAX_EVENTS_PER_TICK = 256
```

Debe reutilizarse en constructor, validación, restauración y tests.

No debe moverse a `OrganismLimits`, porque es una restricción de telemetría.

### 6.2. `modeling/culture.py`

Hay límites nombrados, pero también literales relevantes para assessments, deliveries, composición, half-life y rangos de tick.

Recomendación de nombres:

```python
MAX_ASSESSMENTS = 1024
MAX_DELIVERIES = 4096
DEFAULT_COMPOSITION_THRESHOLD = 64
DEFAULT_FRESHNESS_HALF_LIFE = 32.0
MAX_TICK_CLASS = 255
```

Deben permanecer en `culture.py`.

### 6.3. `modeling/runtime.py`

Conviene nombrar los límites y factores repetidos para settled requests, patience, almacenamiento, coste y ventanas de aprendizaje.

Ejemplos:

```python
_MAX_SETTLED_REQUESTS = 64
_DEFAULT_REQUEST_PATIENCE = 4
_MAX_ARTIFACT_STORAGE_REFERENCE_BYTES = 256 * 1024 * 1024
_PERSISTENCE_COST_FACTOR = 0.5
```

Estos valores pertenecen al mecanismo de model learning y no son límites generales del organismo.

### 6.4. `registry.py`, `authority.py` y `ledger.py`

Las longitudes de IDs, hashes y capacidades deben distinguirse semánticamente:

1. Longitudes criptográficas o de digest: constantes locales del protocolo.
2. Capacidades del registry: constantes locales del registry.

No todo `64`, `128` o `256` representa la misma política.

## 7. Constantes de `core/body_schema.py` que deben quedarse locales

Deben permanecer en `body_schema.py` los umbrales propios del algoritmo:

```python
_REGION_CHANNEL_SUPPORT_MIN
_REGION_PAIR_SUPPORT_MIN
_REGION_PAIR_DENSITY_MIN
_REGION_MEMBER_COVERAGE_MIN
_REGION_SUPPORT_CAP
_REGION_EVIDENCE_CAP
_REGION_RESTRUCTURE_INTERVAL
_DEPENDENCY_SUPPORT_MIN
_DEPENDENCY_CONFIDENCE_MIN_CLASS
_DEPENDENCY_COUNTER_CAP
```

Definen cuándo se consolida una región, cuándo una relación es fiable, cuándo se permite reestructuración y qué evidencia se conserva. No son límites globales del organismo.

## 8. Constantes duplicadas entre Python y JavaScript

La duplicación entre procesos no es por sí misma incorrecta. El problema aparece cuando dos consumidores deben aplicar la misma invariante contractual y no existe un test de correspondencia.

### Debe compartirse dentro de Observatory

- límites del wire contract;
- versiones del snapshot;
- claves públicas;
- nombres de relaciones;
- formatos de IDs;
- límites que protegen una misma entrada.

### Puede mantenerse separado

- límites de memoria internos del organismo;
- límites de renderizado;
- límites del servidor;
- límites de replay;
- límites de UI;
- límites de algoritmos internos.

## 9. Constantes de `observatory/adapter.py`

### Decisión

- `SCHEMA_VERSION`: mantener en el adaptador si representa el snapshot producido por él.
- `BODY_SCHEMA_SNAPSHOT_VERSION`: mantener junto al contrato body schema de Observatory.
- `ENVELOPE_TYPE`: mantener como constante del wire protocol.
- `_LOSS_CLASS_BOUNDS`: mantener local si solo se utiliza para proyectar y discretizar pérdidas.

Si `server.py`, `adapter.py`, tests y JavaScript conocen simultáneamente la versión del snapshot, esta versión debería vivir en un módulo de contrato de Observatory o en un artefacto contractual generado. No debe trasladarse a `symbiont`.

## 10. Qué no conviene centralizar

### 10.1. Un archivo global `constants.py`

No se recomienda porque sería un cajón de sastre, aumentaría imports cruzados y mezclaría runtime, estudios, UI, física y protocolos.

### 10.2. Todos los números repetidos

No todo `256`, `32`, `64` o `0.5` representa la misma regla. El criterio debe ser semántico, no textual.

### 10.3. Todos los `SCHEMA_VERSION`

No deben fundirse. Cada schema tiene una evolución independiente.

### 10.4. Thresholds de estudios y runtime

No deben centralizarse conjuntamente. Los thresholds evaluator-only deben permanecer aislados del runtime.

## 11. Plan de limpieza propuesto

### Fase 1 — Contratos de Observatory

1. Crear módulo o artefacto contractual para body schema.
2. Extraer de `body-schema.js` y `self-schema.js` límites, relaciones, versiones, clases y patrones comunes.
3. Reutilizarlo desde ambos módulos JavaScript.
4. Mantener una definición equivalente verificable desde Python.
5. Añadir tests de paridad Python/JavaScript.

**Prioridad: alta.**

### Fase 2 — Literales inline de módulos de modelado

Extraer únicamente:

- `MAX_EVENTS_PER_TICK`;
- máximos de culture;
- buffers de runtime privado;
- límites de registry;
- referencias de bytes;
- defaults de patience y ventanas.

**Prioridad: media.**

### Fase 3 — Revisión de schema versions inline

Buscar `"schema_version": 1` y sustituirlo por la constante local cuando el módulo ya disponga de ella. No cambiar valores ni unificar versiones.

**Prioridad: media-baja.**

### Fase 4 — Tests de ownership

Añadir una prueba o herramienta de auditoría que detecte:

- duplicación de límites contractuales;
- divergencia entre Python y JavaScript;
- valores contractuales inline;
- imports prohibidos entre `symbiont` y Observatory.

**Prioridad: media.**

## 12. Tabla final de decisión

| Grupo | Decisión | Destino |
|---|---|---|
| Límites físicos y de recursos del organismo | Mantener centralizado | `core/limits.py` |
| Límites del kernel cognitivo | Mantener separado | `cognition/limits.py` |
| Parámetros fisiológicos | Mantener centralizado | `core/physiology_config.py` |
| Convenciones epistemológicas | Mantener centralizado | `core/epistemic.py` |
| Defaults del residente | Mantener local al runtime | `core/runtime_defaults.py` |
| Defaults del servidor Observatory | Mantener local a Observatory | `observatory/config.py` |
| Límites de ingesta Observatory | Centralizar dentro de Observatory | contrato de ingesta |
| Límites de body schema internos | Derivar de `OrganismLimits` | `core/body_schema.py` |
| Límites de body schema JS | Compartir dentro de Observatory | contrato JS/JSON |
| Umbrales del algoritmo body schema | Mantener locales | `core/body_schema.py` |
| Schema versions | Mantener por contrato | módulo propietario |
| Enums y estados | Mantener en su dominio | módulo propietario |
| Seeds de estudios | Mantener locales | estudio/protocolo |
| Métricas evaluator-only | Mantener locales | evaluator/study |
| Física 3D | Mantener local | `physics3d` |
| UI/rendering | Mantener local | módulos Observatory |
| Literales repetidos en modelado | Nombrar localmente | módulo propietario |
| Archivo global `constants.py` | No crear | — |

## 13. Dictamen

La mayor parte de las constantes están correctamente ubicadas. El repositorio no necesita una centralización masiva. La arquitectura ya distingue adecuadamente entre límites, fisiología, epistemología, operación, contratos, experimentos y visualización.

La intervención con mejor relación riesgo/beneficio es:

1. Resolver la duplicación del contrato de body schema entre Python y JavaScript de Observatory.
2. Extraer literales inline repetidos dentro de sus propios módulos.
3. Mantener separadas las familias de configuración existentes.
4. No crear un almacén global de constantes.

**Estado de esta revisión:** diagnóstico completado; no se han aplicado cambios funcionales ni se ha ejecutado la suite de tests.
