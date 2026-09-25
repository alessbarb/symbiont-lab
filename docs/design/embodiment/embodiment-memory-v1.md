---
id: design.embodiment.embodiment-memory-v1
title: "Embodiment Memory V1"
document_type: design
domain: embodiment
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Spec — Embodiment Memory v1

Status: **proposed canonical architecture**.

Date: 2026-09-24.

This specification responds to the second finding of the longitudinal experiment:
the Symbiont preserves identity and general cognition between bodies, but when
it returns to an already known morphology it relearns too much from scratch.

Objective:

> **Allow recognition and reaccess to historical body knowledge without
> introducing anatomical mappings or returning authority to old evidence without
> present validation.**

---

## 1. Principles

1. Body knowledge belongs to a specific embodiment.
2. Changing contract does not erase body history.
3. Returning to a known contract must be faster than learning it from
   scratch.
4. Lab cannot assert semantic equivalences between channels.
5. Historical knowledge enters as hypothesis, never as operative truth.
6. Reactivation requires evidence from the current body.

---

## 2. Observed problem

Experimental sequence:

```text
H1 -> H2 -> H3 -> Crawler -> Asymmetric -> H6
```

In H3 there existed:

- developed body schema;
- motor/primitive readouts;
- sensorimotor primitives;
- active private model.

Upon returning to humanoid in H6, the system preserved the history, but the runtime
did not have a sufficiently rich recoverable embodiment memory. The
result was motor reconstruction from an almost empty surface.

This protects against false transfer, but wastes legitimately historical
knowledge.

---

## 3. New entity: `EmbodimentMemory`

Each known contract can have a consolidated memory.

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

It does not contain organism-facing anatomical names.

### 3.1 Contract fingerprint

Must derive solely from the opaque contract and relevant constitution:

- body contract version;
- receptor count;
- effector count;
- opaque receptor identity scheme;
- opaque effector identity scheme;
- motor slot constitution hash.

Do not use:

- display name;
- anatomical labels;
- observer semantics.

---

## 4. States of historical knowledge

An `EmbodimentMemory` can be:

- `historical`: archived, without authority;
- `candidate`: current contract matches and can be tested;
- `revalidating`: present evidence ongoing;
- `supported`: current evidence confirms part of the knowledge;
- `contradicted`: current evidence refutes it;
- `retired`: no longer deserves reactivation attempts.

The transition cannot depend on human body_kind.

---

## 5. What is archived

### 5.1 Historical body schema

Save:

- opaque parts/connections;
- learned dependencies;
- aggregated confidence/support;
- revision/topology revision.

Do not restore it directly as active schema.

### 5.2 Sensorimotor knowledge

Save:

- primitives;
- effect relations;
- causal support;
- learned costs;
- horizon stats;
- relevant use counts.

Do not save:

- pending observations;
- transient proprioception;
- actuator health from the old body.

### 5.3 Motor cognitive surface

Save the body-specific subgraph:

- motor readouts;
- primitive readouts;
- edges that connect them with general cognition;
- support/utility.

Upon changing contract it must exit the active graph.

Upon returning to the same contract it can enter as candidate surface.

### 5.4 Private models

Preserve references and historical state.

A model learned in another contract:

- cannot be ACTIVE by inheritance;
- can return to be candidate if the contract matches;
- needs revalidation with current experience.

---

## 6. Re-embodiment with different contract

```text
current contract != historical contract
```

Actions:

1. archive active body knowledge;
2. create fresh active BodySchema;
3. create fresh sensorimotor surface;
4. degrade/revoke authority of the body private model;
5. maintain general cognition;
6. maintain EmbodimentMemory intact.

Do not attempt mapping.

---

## 7. Re-embodiment with known contract

```text
current contract fingerprint == historical fingerprint
```

Do not automatically restore.

Process:

```text
fresh body
  -> candidate historical memory
  -> bounded revalidation
  -> selective reactivation
```

### 7.1 Revalidation

Must use natural evidence from the current body:

- action;
- observed effect;
- causal consistency;
- prediction error;
- repeated support.

Forbidden:

- marking a primitive valid just because the ID matches;
- mapping anatomy;
- skipping current evidence.

### 7.2 Partial reactivation

The unit of reactivation must be granular.

For example:

- a primitive can return to `supported`;
- another can become contradicted;
- a body predictor can reactivate;
- another cannot.

Never "restore the whole humanoid".

---

## 8. Cross-body invariants

Body memory allows a subsequent layer of consolidation.

Three categories:

### A. Body-specific

```text
valid only under contract X
```

### B. Recurrent

```text
appears in several contracts with different realization
```

### C. Body-invariant

```text
regularity that survives contract changes
```

Do not create cross-body equivalences by nominal similarity. Only by repeated
evidence across epochs.

---

## 9. Checkpoint

Add a bounded section:

```json
"embodiment_memory": {
  "schema_version": 1,
  "contracts": [...]
}
```

Limits:

- maximum N historical contracts;
- maximum M primitives per contract;
- maximum K body-specific readouts/edges;
- bounded private model refs;
- no raw telemetry.

Eviction policy:

1. retired/contradicted of low support;
2. memories never revalidated and old;
3. preserve at least the current contract and the last known one.

---

## 10. Tests

### M1 — changed contract

H -> C:

- H motor surface disappears from the active graph;
- remains archived;
- is not activated by matching IDs.

### M2 — return to known contract

H -> C -> H:

- H memory appears as candidate;
- active body schema starts fresh;
- there is no active primitive without evidence.

### M3 — successful revalidation

A historical primitive with reproduced evidence recovers supported state.

### M4 — contradiction

If the same physical contract produces incompatible consequences, the historical
primitive is not reactivated.

### M5 — model authority

Historical private model never becomes ACTIVE by simple restore.

### M6 — no anatomy leakage

Organism-facing checkpoint does not contain human names of the body.

---

## 11. Study metrics

For each return to a known contract measure:

- ticks until first revalidated primitive;
- ticks until first supported motor readout;
- time until comparable schema confidence;
- number of confirmed historical hypotheses;
- contradicted number;
- survival delta against learning from scratch;
- energetic cost of reacclimation.

---

## 12. Acceptance criteria

EmbodimentMemory is validated when:

1. returning to a known contract is not equivalent to blindly restoring;
2. it is also not equivalent to forgetting everything;
3. historical knowledge only recovers authority by current evidence;
4. there is no anatomical mapping introduced by Lab;
5. the return can be measurably faster if the prior knowledge continues
   being valid.
