---
id: design.embodiment.longitudinal-reembodiment-v1
title: "Longitudinal Reembodiment V1"
document_type: design
domain: embodiment
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Spec Package — Longitudinal Re-embodiment v1

Status: **proposed canonical direction**.

Date: 2026-09-24.

This document groups the findings of the first longitudinal specimen that completed:

```text
anthropomorphic
 -> anthropomorphic
 -> anthropomorphic
 -> crawler
 -> asymmetric
 -> anthropomorphic
```

and translates those findings into architectural requirements.

Associated normative documents:

- [Temporal Separation Symbiont / Body](symbiont-body-temporal-separation-v1.md)
- [Embodiment Memory](embodiment-memory-v1.md)
- [Embodiment Epoch Summary](embodiment-epoch-summary-v1.md)
- [Temporal Decontamination Audit](../../research/audits/current/2026-09-temporal-decontamination.md)

---

## 1. Observed experimental result

The individual maintained the same `organism_id` for six epochs.

Recorded sequence:

| Epoch | Body | Global start | Global end | State on close |
| --- | --- | ---: | ---: | --- |
| 1 | anthropomorphic-v4 | 0 | 4513 | dead |
| 2 | anthropomorphic-v4 | 4513 | 8922 | dead |
| 3 | anthropomorphic-v4 | 8922 | 13323 | dead |
| 4 | crawler-v1 | 13323 | 16775 | dead |
| 5 | asymmetric-v1 | 16775 | 19948 | dormant |
| 6 | anthropomorphic-v4 | 19948 | 23315 | dead |

Final checkpoint:

- `saved_at_tick = 23315`;
- `experience_ledger = 2048` records, at maximum capacity;
- `episodic_memory = 52` episodes;
- `motor_primitives = 5`;
- actuator candidates: 2 active, 60 dormant;
- CognitiveGraph: 192 nodes / 606 edges;
- 128 sense, 32 concept, 30 predictor, 2 readout;
- private models: 1 active, 3 degraded, 12 retired;
- BodySchema: `partial`, 150 parts;
- body final: energy 0, integrity ~0.448, senescence 1.0.

---

## 2. What this experiment DOES demonstrate

### 2.1 Identity continuity

The same Symbiont can:

- persist beyond the death of a body;
- re-embody in another contract;
- maintain memory/cognition/models;
- produce new body learning;
- return to a known morphology.

This validates the conceptual separation:

```text
Symbiont identity != Body identity
```

### 2.2 Cognitive persistence

A general collapse of the cognitive core after multiple re-embodiments is not observed.

At the end there still exist:

- active CognitiveGraph;
- predictors;
- episodic memory;
- active private model;
- sensorimotor primitives;
- motor learning in progress.

Therefore, there is not enough evidence to immediately increase:

- node budget;
- concept budget;
- model count;
- learning rate;
- plasticity;
- memory raw capacity.

### 2.3 Cross-contract re-embodiment

Crawler and asymmetric produce new contracts without preventing the continuity of the individual.

The system can withdraw old body authority and reconstruct a new sensorimotor surface.

---

## 3. What it DOES NOT demonstrate yet

The observed differences in duration between bodies are not interpretable as a clean morphological effect.

Reason:

```text
body.age_ticks <- symbiont global tick
```

The new body de facto inherited the historical age of the Symbiont.

This triggers premature senescence and contaminates:

- lifespan;
- structural wear;
- energy trajectory;
- death age;
- comparisons between contracts.

The epochs of the first study must be labeled:

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

## 4. Finding P0 — temporal separation

Mandatory to implement:

```text
symbiont_tick
body_age_ticks
knowledge-local time
```

`Symbiont biological age` does not exist.

The Symbiont can be:

- naive;
- experienced;
- consolidated;
- reorganizing;

but not:

- young;
- mature;
- old;
- senescent;

by simple passage of time.

---

## 5. Finding P1 — insufficient body memory

The current system prevents an incorrect transfer between contracts, but also loses too much advantage when returning to a known contract.

We need:

```text
EmbodimentMemory
```

that preserves historical body knowledge as a revalidatable hypothesis.

Core requirement:

> Returning to a known body can be neither blind restoration nor amnesia.

---

## 6. Finding P1 — insufficient epoch history

Current `embodiment_history` does not preserve enough terminal metrics.

We need:

```text
EmbodimentEpochSummary
```

immutable and bounded.

It must allow reconstructing longitudinal history without external raw telemetry.

---

## 7. Finding P1 — experience ledger full

The ledger ends at:

```text
2048 / 2048
```

This does not imply that it should be expanded.

Decision:

- maintain bounded raw experience;
- strengthen longitudinal consolidation;
- preserve relevant episodes;
- consolidate body-specific and cross-body knowledge.

Do not resolve with unlimited growth of the checkpoint.

---

## 8. Naming finding — BodySchema `partial`

The `partial` state must not be interpreted as a failure.

Currently BodySchema does not represent a true `complete` terminal state.

Recommendation for semantic evolution:

```text
undeveloped
developing
established
revising
```

The transition must be based on evidence/support/confidence, not on percentage of known anatomy.

It is not P0.

---

## 9. What NOT to adjust yet

Until repeating the protocol without temporal contamination, do not modify:

### Metabolism

Do not increase `max_energy` or reduce costs to "make it live longer".

The observed energy death may be biased by premature senescence.

### Cognitive budgets

Do not increase:

- nodes;
- concepts;
- edges;
- predictor budget.

The graph remains active and does not show terminal freeze due to budget.

### SLM

Do not increase number of models or force promotions.

The final organism maintains an active model.

### Plasticity

Do not add plasticity rules by age.

Any future adaptation must respond to evidence, uncertainty, stability, cost or structural pressure.

### Motor thresholds

Do not lower thresholds just because upon returning to the humanoid the motor recovery was slow.

First implement EmbodimentMemory and repeat.

---

## 10. New conceptual model

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

## 11. Implementation order

### P0.1 — Temporal separation

- correct body age;
- separate local/global death;
- migrate checkpoints;
- dual telemetry;
- tests.

### P0.2 — Temporal decontamination audit

Classify all temporal fields.

No new longitudinal study until closing the gate.

### P1.1 — EmbodimentEpochSummary

Close scientific traceability.

### P1.2 — EmbodimentMemory

Allow return to known contract with revalidation.

### P1.3 — BodySchema state semantics

Remove the ambiguity of `partial`.

### P2 — repeat study

Repeat:

```text
H -> H -> H -> C -> A -> H
```

with the same conditions.

Only then compare:

- lifespan;
- energy efficiency;
- reacclimation;
- motor transfer;
- return-to-known-body advantage.

---

## 12. Subsequent experimental gate

The next longitudinal study will be valid for morphological comparison only if:

1. fresh body starts with body_age 0;
2. senescence depends on body age;
3. Symbiont historical time continues;
4. epoch summaries record terminal metrics;
5. known-contract return has an EmbodimentMemory candidate;
6. no anatomy mapping enters cognition;
7. seed/config reproducibility is recorded.

---

## 13. Resulting architectural thesis

The evolution of Symbiont must follow this separation:

> **The Body is born, grows, ages and dies.**

> **The Symbiont persists, learns, remembers, reorganizes and accumulates history.**

> **Embodiment is the temporal relationship between both.**

Any implementation that merges these three levels again reintroduces the original conceptual error.
