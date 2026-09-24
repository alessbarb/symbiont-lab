# Spec — Embodiment Memory v1

Status: **proposed canonical architecture**.

Fecha: 2026-09-24.

Esta especificación responde al segundo hallazgo del experimento longitudinal:
el Symbiont conserva identidad y cognición general entre cuerpos, pero cuando
vuelve a una morfología ya conocida reaprende demasiado desde cero.

Objetivo:

> **Permitir reconocimiento y reacceso a conocimiento corporal histórico sin
> introducir mappings anatómicos ni devolver autoridad a evidencia antigua sin
> validación presente.**

---

## 1. Principios

1. El conocimiento corporal pertenece a un embodiment concreto.
2. Cambiar de contract no borra la historia corporal.
3. Volver a un contract conocido debe poder ser más rápido que aprenderlo desde
   cero.
4. Lab no puede afirmar equivalencias semánticas entre canales.
5. Conocimiento histórico entra como hipótesis, nunca como verdad operativa.
6. La reactivación requiere evidencia del body actual.

---

## 2. Problema observado

Secuencia experimental:

```text
H1 -> H2 -> H3 -> Crawler -> Asymmetric -> H6
```

En H3 existían:

- body schema humanoide desarrollado;
- motor/primitive readouts;
- sensorimotor primitives;
- private model activo.

Al volver a humanoide en H6, el sistema conservó la historia, pero el runtime
no disponía de una memoria de embodiment recuperable suficientemente rica. El
resultado fue reconstrucción motora desde una superficie casi vacía.

Esto protege contra transferencia falsa, pero desaprovecha conocimiento
legítimamente histórico.

---

## 3. Nueva entidad: `EmbodimentMemory`

Cada contract conocido puede tener una memoria consolidada.

```text
EmbodimentMemory
  contract_fingerprint
  first_seen_epoch
  last_seen_epoch
  body_schema_snapshot
  sensorimotor_knowledge
  motor_cognitive_surface
  private_model_refs
  validation_history
  confidence_state
```

No contiene nombres anatómicos organismo-facing.

### 3.1 Contract fingerprint

Debe derivar únicamente del contrato opaco y constitución relevante:

- body contract version;
- receptor count;
- effector count;
- opaque receptor identity scheme;
- opaque effector identity scheme;
- motor slot constitution hash.

No usar:

- display name;
- anatomical labels;
- observer semantics.

---

## 4. Estados de conocimiento histórico

Un `EmbodimentMemory` puede estar:

- `historical`: archivado, sin autoridad;
- `candidate`: contract actual coincide y puede probarse;
- `revalidating`: evidencia presente en curso;
- `supported`: evidencia actual confirma parte del conocimiento;
- `contradicted`: evidencia actual lo refuta;
- `retired`: ya no merece intentos de reactivación.

La transición no puede depender del body_kind humano.

---

## 5. Qué se archiva

### 5.1 Body schema histórico

Guardar:

- partes/conexiones opacas;
- dependencias aprendidas;
- confidence/support agregados;
- revisión/topology revision.

No restaurarlo directamente como schema activo.

### 5.2 Sensorimotor knowledge

Guardar:

- primitives;
- effect relations;
- causal support;
- costes aprendidos;
- horizon stats;
- use counts relevantes.

No guardar:

- pending observations;
- transient proprioception;
- actuator health del body viejo.

### 5.3 Motor cognitive surface

Guardar el subgrafo body-specific:

- motor readouts;
- primitive readouts;
- edges que los conectan con cognición general;
- support/utility.

Al cambiar de contract debe salir del grafo activo.

Al volver al mismo contract puede entrar como candidate surface.

### 5.4 Private models

Conservar referencias y estado histórico.

Un modelo aprendido en otro contract:

- no puede ser ACTIVE por herencia;
- puede volver a ser candidate si el contract coincide;
- necesita revalidación con experiencia actual.

---

## 6. Re-embodiment con contract distinto

```text
current contract != historical contract
```

Acciones:

1. archivar conocimiento corporal activo;
2. crear BodySchema activo fresco;
3. crear sensorimotor surface fresca;
4. degradar/revocar autoridad del private model corporal;
5. mantener cognición general;
6. mantener EmbodimentMemory intacta.

No intentar mapping.

---

## 7. Re-embodiment con contract conocido

```text
current contract fingerprint == historical fingerprint
```

No restaurar automáticamente.

Proceso:

```text
fresh body
  -> candidate historical memory
  -> bounded revalidation
  -> selective reactivation
```

### 7.1 Revalidation

Debe usar evidencia natural del body actual:

- acción;
- efecto observado;
- consistencia causal;
- prediction error;
- repeated support.

Prohibido:

- marcar una primitive válida solo porque el ID coincide;
- mapear anatomy;
- saltarse evidencia actual.

### 7.2 Reactivación parcial

La unidad de reactivación debe ser granular.

Por ejemplo:

- una primitive puede volver a `supported`;
- otra puede quedar contradicha;
- un predictor corporal puede reactivarse;
- otro no.

Nunca "restaurar todo el humanoide".

---

## 8. Cross-body invariants

La memoria corporal permite una capa posterior de consolidación.

Tres categorías:

### A. Body-specific

```text
válido solo bajo contract X
```

### B. Recurrente

```text
aparece en varios contracts con distinta realización
```

### C. Body-invariant

```text
regularidad que sobrevive a cambios de contract
```

No crear equivalencias cross-body por similitud nominal. Solo por evidencia
repetida a través de epochs.

---

## 9. Checkpoint

Añadir una sección bounded:

```json
"embodiment_memory": {
  "schema_version": 1,
  "contracts": [...]
}
```

Límites:

- máximo N contracts históricos;
- máximo M primitives por contract;
- máximo K readouts/edges body-specific;
- private model refs bounded;
- no raw telemetry.

Eviction policy:

1. retired/contradicted de bajo support;
2. memories nunca revalidadas y antiguas;
3. conservar al menos el contract actual y el último conocido.

---

## 10. Tests

### M1 — changed contract

H -> C:

- H motor surface desaparece del active graph;
- queda archivada;
- no se activa por IDs coincidentes.

### M2 — return to known contract

H -> C -> H:

- H memory aparece como candidate;
- active body schema empieza fresco;
- no hay primitive activa sin evidencia.

### M3 — successful revalidation

Una primitive histórica con evidencia reproducida recupera estado supported.

### M4 — contradiction

Si el mismo contract físico produce consecuencias incompatibles, la primitive
histórica no se reactiva.

### M5 — model authority

Private model histórico nunca vuelve ACTIVE por simple restore.

### M6 — no anatomy leakage

Checkpoint organismo-facing no contiene nombres humanos del body.

---

## 11. Métricas de estudio

Para cada retorno a contract conocido medir:

- ticks hasta primera primitive revalidada;
- ticks hasta primer motor readout supported;
- tiempo hasta schema confidence comparable;
- número de hipótesis históricas confirmadas;
- número contradicho;
- survival delta frente a aprendizaje desde cero;
- coste energético de reaclimatación.

---

## 12. Criterio de aceptación

EmbodimentMemory queda validada cuando:

1. volver a un contract conocido no equivale a restaurar ciegamente;
2. tampoco equivale a olvidar todo;
3. el conocimiento histórico solo recupera autoridad por evidencia actual;
4. no existe mapping anatómico introducido por Lab;
5. el retorno puede ser mediblemente más rápido si el conocimiento previo sigue
   siendo válido.
