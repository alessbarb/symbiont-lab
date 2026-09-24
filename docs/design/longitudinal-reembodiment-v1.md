# Spec Package — Longitudinal Re-embodiment v1

Status: **proposed canonical direction**.

Fecha: 2026-09-24.

Este documento agrupa los hallazgos del primer espécimen longitudinal que
completó:

```text
anthropomorphic
 -> anthropomorphic
 -> anthropomorphic
 -> crawler
 -> asymmetric
 -> anthropomorphic
```

y traduce esos hallazgos en requisitos de arquitectura.

Documentos normativos asociados:

- [Separación temporal Symbiont / Body](symbiont-body-temporal-separation-v1.md)
- [Embodiment Memory](embodiment-memory-v1.md)
- [Embodiment Epoch Summary](embodiment-epoch-summary-v1.md)
- [Temporal Decontamination Audit](../../research/audits/current/2026-09-temporal-decontamination.md)

---

## 1. Resultado experimental observado

El individuo mantuvo el mismo `organism_id` durante seis epochs.

Secuencia registrada:

| Epoch | Body | Inicio global | Fin global | Estado al cerrar |
| --- | --- | ---: | ---: | --- |
| 1 | anthropomorphic-v4 | 0 | 4513 | dead |
| 2 | anthropomorphic-v4 | 4513 | 8922 | dead |
| 3 | anthropomorphic-v4 | 8922 | 13323 | dead |
| 4 | crawler-v1 | 13323 | 16775 | dead |
| 5 | asymmetric-v1 | 16775 | 19948 | dormant |
| 6 | anthropomorphic-v4 | 19948 | 23315 | dead |

Checkpoint final:

- `saved_at_tick = 23315`;
- `experience_ledger = 2048` registros, en capacidad máxima;
- `episodic_memory = 52` episodios;
- `motor_primitives = 5`;
- actuator candidates: 2 active, 60 dormant;
- Cognitive Graph: 192 nodes / 606 edges;
- 128 sense, 32 concept, 30 predictor, 2 readout;
- private models: 1 active, 3 degraded, 12 retired;
- BodySchema: `partial`, 150 parts;
- body final: energy 0, integrity ~0.448, senescence 1.0.

---

## 2. Qué sí demuestra este experimento

### 2.1 Continuidad de identidad

El mismo Symbiont puede:

- persistir más allá de la muerte de un body;
- re-embody en otro contract;
- mantener memoria/cognición/modelos;
- producir nuevo aprendizaje corporal;
- volver a una morfología conocida.

Esto valida la separación conceptual:

```text
Symbiont identity != Body identity
```

### 2.2 Persistencia cognitiva

No se observa un colapso general del núcleo cognitivo tras múltiples
re-embodiments.

Al final siguen existiendo:

- cognitive graph activo;
- predictors;
- episodic memory;
- private model activo;
- sensorimotor primitives;
- aprendizaje motor en curso.

Por tanto, no existe evidencia suficiente para aumentar de inmediato:

- node budget;
- concept budget;
- model count;
- learning rate;
- plasticity;
- memory raw capacity.

### 2.3 Re-embodiment cross-contract

Crawler y asymmetric producen nuevos contracts sin impedir continuidad del
individuo.

El sistema puede retirar autoridad corporal antigua y reconstruir nueva
superficie sensorimotora.

---

## 3. Qué NO demuestra todavía

Las diferencias observadas de duración entre bodies no son interpretables como
efecto morfológico limpio.

Razón:

```text
body.age_ticks <- symbiont global tick
```

El body nuevo heredaba de facto la edad histórica del Symbiont.

Esto activa senescencia prematura y contamina:

- lifespan;
- structural wear;
- energy trajectory;
- death age;
- comparisons entre contracts.

Los epochs del primer estudio deben etiquetarse:

```text
VALID for:
- identity continuity
- checkpoint continuity
- cross-contract learning existence
- persistence architecture

CONTAMINATED for:
- body lifespan comparison
- senescence comparison
- morphology efficiency claims
```

---

## 4. Hallazgo P0 — separación de tiempo

Implementar obligatoriamente:

```text
symbiont_tick
body_age_ticks
knowledge-local time
```

No existe `Symbiont biological age`.

El Symbiont puede ser:

- naive;
- experienced;
- consolidated;
- reorganizing;

pero no:

- young;
- mature;
- old;
- senescent;

por simple transcurso temporal.

---

## 5. Hallazgo P1 — memoria corporal insuficiente

El sistema actual evita una transferencia incorrecta entre contracts, pero
también pierde demasiada ventaja al volver a un contract conocido.

Necesitamos:

```text
EmbodimentMemory
```

que preserve conocimiento corporal histórico como hipótesis revalidable.

Requisito central:

> Volver a un cuerpo conocido no puede ser ni restauración ciega ni amnesia.

---

## 6. Hallazgo P1 — historia de epoch insuficiente

`embodiment_history` actual no preserva suficientes métricas terminales.

Necesitamos:

```text
EmbodimentEpochSummary
```

inmutable y bounded.

Debe permitir reconstruir historia longitudinal sin telemetría raw externa.

---

## 7. Hallazgo P1 — experience ledger lleno

El ledger termina en:

```text
2048 / 2048
```

Esto no implica que deba ampliarse.

Decisión:

- mantener bounded raw experience;
- fortalecer consolidación longitudinal;
- conservar episodios relevantes;
- consolidar body-specific y cross-body knowledge.

No resolver con crecimiento ilimitado del checkpoint.

---

## 8. Hallazgo de naming — BodySchema `partial`

El estado `partial` no debe interpretarse como fracaso.

Actualmente BodySchema no representa un verdadero estado terminal
`complete`.

Recomendación de evolución semántica:

```text
undeveloped
developing
established
revising
```

La transición debe basarse en evidencia/support/confidence, no en porcentaje de
anatomía conocida.

No es P0.

---

## 9. Qué NO ajustar todavía

Hasta repetir el protocolo sin contaminación temporal, no modificar:

### Metabolismo

No aumentar `max_energy` ni reducir costes para "hacer que viva más".

La muerte energética observada puede estar sesgada por senescencia prematura.

### Cognitive budgets

No aumentar:

- nodes;
- concepts;
- edges;
- predictor budget.

El graph sigue activo y no muestra freeze terminal por budget.

### SLM

No aumentar número de modelos ni forzar promotions.

El organismo final mantiene un modelo activo.

### Plasticidad

No añadir reglas de plasticidad por edad.

Cualquier adaptación futura debe responder a evidencia, incertidumbre,
estabilidad, coste o presión estructural.

### Motor thresholds

No bajar thresholds solo porque al volver al humanoide la recuperación motora
fue lenta.

Primero implementar EmbodimentMemory y repetir.

---

## 10. Nuevo modelo conceptual

```text
SYMBIONT
  identity
  symbiont_tick
  cognition
  memory
  models
  embodiment memories
  longitudinal history
       |
       v
EMBODIMENT EPOCH
  contract
  reacclimation
  body schema
  sensorimotor knowledge
       |
       v
BODY
  body_age_ticks
  growth
  energy
  fatigue
  integrity
  senescence
  death
```

---

## 11. Orden de implementación

### P0.1 — Temporal separation

- corregir body age;
- separar death local/global;
- migrar checkpoints;
- telemetría dual;
- tests.

### P0.2 — Temporal decontamination audit

Clasificar todos los campos temporales.

Ningún estudio longitudinal nuevo hasta cerrar el gate.

### P1.1 — EmbodimentEpochSummary

Cerrar la trazabilidad científica.

### P1.2 — EmbodimentMemory

Permitir retorno a contract conocido con revalidación.

### P1.3 — BodySchema state semantics

Eliminar la ambigüedad de `partial`.

### P2 — repetir estudio

Repetir:

```text
H -> H -> H -> C -> A -> H
```

con las mismas condiciones.

Solo entonces comparar:

- lifespan;
- energy efficiency;
- reacclimation;
- motor transfer;
- return-to-known-body advantage.

---

## 12. Gate experimental posterior

El siguiente estudio longitudinal será válido para comparación morfológica solo
si:

1. fresh body empieza con body_age 0;
2. senescence depende de body age;
3. Symbiont historical time continúa;
4. epoch summaries registran métricas terminales;
5. known-contract return dispone de EmbodimentMemory candidate;
6. no anatomy mapping entra en cognition;
7. reproducibilidad de seed/config queda registrada.

---

## 13. Tesis arquitectónica resultante

La evolución de Symbiont debe seguir esta separación:

> **El Body nace, crece, envejece y muere.**

> **El Symbiont persiste, aprende, recuerda, reorganiza y acumula historia.**

> **El Embodiment es la relación temporal entre ambos.**

Cualquier implementación que vuelva a fusionar esos tres niveles reintroduce
el error conceptual original.
