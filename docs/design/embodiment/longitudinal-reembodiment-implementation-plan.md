---
id: design.embodiment.longitudinal-reembodiment-implementation-plan
title: "Longitudinal Reembodiment Implementation Plan"
document_type: design
domain: embodiment
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Implementation Plan — Longitudinal Re-embodiment v1

Status: **implementation-ready**.

This document translates the longitudinal specs into concrete code changes.

---

## P0 — Temporal separation

### 1. `src/symbiont/core/embodiment/physiology.py`

Objective:

- keep `LivingBodyState` as the owner of physiology;
- change the semantics of `age_ticks` to body-local;
- keep `advance_age()` as the only increment operation;
- document `death_tick` as body-local.

Do not change serialized keys yet unless necessary.

Add:

- local age invariants;
- explicit documentation;
- validation of `death_tick <= age_ticks` when applicable.

Future schema:

```text
body_age_ticks
body_death_age_ticks
```

but name migration can be separated from semantic correction.

### 2. `src/symbiont/core/orchestration/runtime.py`

Remove:

```python
self._living_body_state.age_ticks = self._tick_count
```

Replace with:

```python
self._living_body_state.advance_age()
```

Keep `self._tick_count` as global history.

Audit calls to:

- `PhysiologyController.advance(... tick=...)`;
- `mark_dead(tick)`;
- offspring creation;
- restore.

Separate arguments if an API needs:

```text
symbiont_tick
body_age_tick
```

Do not pass the global when the expected semantics is body-local.

### 3. `src/symbiont/core/embodiment/ontogeny.py`

Does not require a new state owner.

Verify that:

```python
body.age_ticks >= senescence_start_ticks
```

now exclusively means body-local.

Add test for `symbiont_tick` independence.

### 4. `src/symbiont_lab/physics3d/reembodiment.py`

Fresh body:

- age 0;
- senescence 0;
- fresh canonical growth state;
- death tick null;
- complete fresh physiology.

Do not copy any temporal physiological field from previous.

Add migration helper:

```text
repair_contaminated_body_age(payload)
```

only for clearly identifiable checkpoint.

### 5. `src/symbiont_lab/physics3d/runtime.py`

Expose via telemetry:

- `symbiont_tick`;
- `body_age_ticks`;
- `embodiment_epoch`;
- body senescence;
- reacclimation.

Do not send these names as cognitive signals.

### 6. `src/symbiont_lab/observation/projection.py`

Separate observer-only projection:

```json
{
  "symbiont_tick": 25000,
  "embodiment_epoch": 7,
  "body_age_ticks": 812
}
```

---

## P0 — Checkpoint migration

### Detector

For checkpoint with lifecycle:

```text
started = current.started_tick
saved = saved_at_tick
expected_local = saved - started
stored = living_body.age_ticks
```

Strong contamination if:

```text
started > 0
stored approx saved
stored != expected_local
```

The migration:

- corrects `age_ticks`;
- corrects `death_tick` if it represents the same contaminated clock;
- does not touch energy/integrity/senescence retrospectively;
- marks migration metadata.

Important:

> Do not attempt to retrospectively "de-age" integrity or energy of a body
> that already lived under contaminated senescence.

Those runs remain scientifically contaminated.

The migration only allows continuing the checkpoint with correct semantics in a
new body.

---

## P1 — EmbodimentEpochSummary

### 7. `src/symbiont_lab/physics3d/reembodiment.py`

Add dataclass/model:

```text
EmbodimentEpochSummary
```

Close summary before incrementing epoch.

### 8. `src/symbiont_lab/physics3d/runtime.py`

Keep accumulators bounded by epoch:

- absorbed material;
- mechanical work;
- cost;
- repair;
- time in vital states;
- motor learning counters.

### 9. `src/symbiont_lab/physics3d/engine.py`

At final checkpoint:

- close epoch if body dies or re-embodies;
- do not close epoch on stop/resume of the same body.

### 10. `src/symbiont_lab/app/physics3d_runs.py`

Show relevant summary in catalog:

- current epoch;
- previous end reason;
- body age;
- lifetime;
- last contract.

---

## P1 — EmbodimentMemory

### 11. Suggested new module

```text
src/symbiont/core/embodiment/memory.py
```

or, if it remains Physics3D-specific initially:

```text
src/symbiont_lab/physics3d/embodiment_memory.py
```

Architectural preference: core only if the concept ceases to depend on
Physics3D.

Types:

```text
EmbodimentContractFingerprint
EmbodimentMemory
HistoricalMotorSurface
HistoricalPrimitive
RevalidationState
```

### 12. `src/symbiont_lab/physics3d/reembodiment.py`

On contract exit:

- consolidate current body-specific state;
- archive;
- remove active authority.

On entry:

```text
different fingerprint -> fresh
same historical fingerprint -> candidate revalidation
```

### 13. `src/symbiont/core/orchestration/runtime.py`

Does not need to know `body_kind`.

Must accept a bounded set of opaque historical hypotheses and subject them to
the same evidence/support rules as new knowledge.

### 14. `src/symbiont/modeling/*`

Historical private model:

- preserve artifact;
- ACTIVE -> DEGRADED on contract change;
- candidate on known-contract return;
- reactivation requires validation.

---

## P1 — BodySchema naming

### 15. `src/symbiont/core/embodiment/body_schema.py`

Review:

```text
undeveloped
partial
```

Proposal:

```text
undeveloped
developing
established
revising
```

Gates by:

- support;
- stable dependencies;
- observation count;
- confidence/consistency;

not by anatomical completeness.

---

## Temporal audit

### 16. `src/symbiont/core/embodiment/development.py`

Classify each counter.

`declining` cannot mean "old Symbiont".

### 17. `src/symbiont/core/embodiment/degradation.py`

Document its `aging_ticks` as T-K (retention lifecycle).

Consider a later rename to reduce ambiguity.

### 18. `src/symbiont/sensory/*`

`sensor.age_ticks` = age of sensory structure, T-K.

Do not connect to Symbiont senescence.

### 19. `src/symbiont/cognition/*`

`edge.age_ticks`, support, recency = T-K.

Search for any global-age driven decay.

### 20. `src/symbiont/modeling/*`

Model staleness must be evidence/validation-driven.

---

## New tests

### Core

Create/update:

```text
tests/unit/core/test_temporal_domains.py
tests/unit/core/test_ontogeny.py
tests/unit/core/test_physiology.py
```

Cases:

- old Symbiont + fresh body;
- same body resume;
- fresh re-embodiment;
- senescence independence;
- death local tick.

### Physics3D

```text
tests/unit/lab/physics3d/test_reembodiment.py
tests/integration/test_physics3d_existing_reuse.py
tests/integration/test_physics3d_temporal_domains.py
```

### Memory

```text
tests/unit/lab/physics3d/test_embodiment_memory.py
tests/integration/test_known_contract_return.py
```

### Summary

```text
tests/unit/lab/physics3d/test_epoch_summary.py
```

---

## Recommended PR order

### PR-T1 — temporal domain fix

Only:

- body age;
- death tick semantics;
- migration;
- tests.

Do not mix EmbodimentMemory.

### PR-T2 — epoch summaries

Observer/persistence only.

### PR-T3 — EmbodimentMemory archival

Archive correctly, without reactivating yet.

### PR-T4 — known-contract revalidation

Candidate -> supported/contradicted.

### PR-T5 — BodySchema states

Naming/telemetry after closing mechanisms.

### PR-T6 — longitudinal study v2

Preregistered repetition.

---

## Do not mix in these PRs

- metabolism tuning;
- energy capacity changes;
- new rewards;
- locomotion targets;
- model-size increases;
- cognitive budget increases;
- hand-written cross-body mappings.

---

## Definition of done

The longitudinal v1 package is implemented when:

1. the three temporal domains are separated;
2. fresh body always is born with local physiological age 0;
3. senescence does not see `symbiont_tick`;
4. epoch history is scientifically reconstructible;
5. historical body knowledge is neither lost nor restored blindly;
6. known-contract return is revalidated by evidence;
7. the study H->H->H->C->A->H can be repeated without known contamination.
