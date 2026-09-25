---
id: design.embodiment.embodiment-epoch-summary-v1
title: "Embodiment Epoch Summary V1"
document_type: design
domain: embodiment
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Spec — Embodiment Epoch Summary v1

Status: **proposed observer/persistence contract**.

Date: 2026-09-24.

Objective:

> **To be able to reconstruct the complete bodily history of a Symbiont from a
> checkpoint without depending on preserving all external raw telemetry.**

The longitudinal experiment revealed that `embodiment_history` preserves body
identity, ticks, and part of the archived knowledge, but not a sufficient
physiological/cognitive summary to compare epochs reliably.

---

## 1. New entity

```text
EmbodimentEpochSummary
```

Belongs to persistence/observer. It is not a signal for cognition.

Each closed epoch generates exactly one immutable summary.

Minimum fields:

```text
epoch
contract_fingerprint
body_kind_observer_only

started_at_symbiont_tick
ended_at_symbiont_tick
duration_body_ticks

end_reason
body_vital_state
body_death_age_ticks

final_energy_ratio
final_structural_integrity
final_senescence
final_fatigue

absorbed_material_total
mechanical_work_total
physiological_cost_total

body_schema_state
body_schema_part_count
motor_primitive_count
motor_candidate_count
motor_supported_count
motor_readout_count
predictor_count

private_model_state_counts
active_private_model_id

reacclimation_ticks_consumed
reacclimation_completed
```

---

## 2. End reason

Closed values:

- `dead_energy`;
- `dead_structure`;
- `dead_unrecoverable_pressure`;
- `stopped_alive`;
- `suspended`;
- `reembodied_alive`;
- `startup_failed`;
- `unknown`.

Do not infer ambiguous causes.

If several terminal conditions are simultaneous, record:

```text
end_reason = unknown
terminal_facts = [...]
```

observer-side.

---

## 3. Two time coordinates

Each summary must save both:

```text
started_at_symbiont_tick
ended_at_symbiont_tick
duration_body_ticks
```

Never derive future body age from global tick except for explicit migration.

Invariant:

```text
duration_body_ticks == final_body_age_ticks
```

for a body that started fresh.

For resume of the same body:

```text
duration_body_ticks
```

includes all its accumulated physical life, not just the last process.

---

## 4. Accumulators per epoch

Do not store complete raw telemetry.

Maintain bounded accumulators during the run:

- absorbed energy;
- physiological cost;
- mechanical work;
- number of repair events;
- number of vital state changes;
- time in stress/dormant/agonizing;
- reacclimation ticks;
- primitives created/revalidated;
- model promotions/degradations.

These accumulators are closed at the end of the epoch.

---

## 5. Immutability

Once closed:

```text
EmbodimentEpochSummary(epoch=N)
```

does not change.

If a migration error is discovered:

- do not rewrite silently;
- add `summary_revision`;
- record `derived_from_checkpoint_schema`;
- allow deterministic regeneration in tooling, not in cognitive runtime.

---

## 6. Bounded history

The checkpoint can maintain:

- last N complete summaries;
- historical aggregates of older epochs.

Do not discard:

- first epoch;
- last epoch of each known contract;
- epochs with contract transitions;
- epochs selected as scientific milestones.

Exact policy must be fixed by budget, not by human semantic value.

---

## 7. Scientific use

Allows comparing:

### Same morphology

```text
H1 vs H2 vs H3
```

### Different morphologies

```text
H vs Crawler vs Asymmetric
```

### Return

```text
H1/H2/H3 vs H6
```

### Alive re-embodiment vs post-mortem

```text
end_reason = reembodied_alive
vs
end_reason = dead_*
```

---

## 8. Tests

### E1 — closure by death

Summary contains:

- local duration;
- vital state dead;
- cause compatible with facts;
- final body age.

### E2 — closure alive

Changing body without death generates:

```text
end_reason = reembodied_alive
```

without fabricating death tick.

### E3 — resume

Stopping and continuing the same body does not create a new epoch.

### E4 — boundedness

Thousands of ticks do not increase the size of the summary boundlessly.

### E5 — no leakage

The summary can contain body_kind because it is observer-side, but it does not enter:

- sensory system;
- cognitive graph;
- model inputs;
- action selector.

---

## 9. Acceptance criteria

From a single `.symbiont` it must be possible to answer deterministically:

- how many bodies it inhabited;
- how long each body lived;
- how it ended;
- what contract it had;
- how much it learned bodily;
- what physiological state it had at the end;
- what private model governed it;
- how long it took to reacclimate;

without needing a separate telemetry ZIP.
