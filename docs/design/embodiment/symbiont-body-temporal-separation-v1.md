---
id: design.general.symbiont-body-temporal-separation-v1
title: "Symbiont Body Temporal Separation V1"
document_type: design
domain: embodiment
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Spec — Temporal Separation Symbiont / Body v1

Status: **proposed canonical architecture**.

Date: 2026-09-24.

This specification stems from the first complete longitudinal re-embodiment experiment:

```text
H -> H -> H -> Crawler -> Asymmetric -> H
```

The experiment demonstrated that the identity, memory, and cognition of the Symbiont can persist across multiple bodies, but it also revealed a temporal contamination inherited from the old `organism == body` model.

The canonical conclusion is:

> **The Symbiont does not age biologically. The Body does.**

> **The Symbiont accumulates history; the Body accumulates physiological age.**

---

## 1. Encountered Problem

The runtime maintains a global historical counter `_tick_count`, which represents the temporal continuity of the Symbiont's identity. After each tick the current code does:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.age_ticks = self._tick_count
```

This was consistent when a Symbiont was born with a single body and both shared their entire life.

It is no longer consistent after introducing re-embodiment.

In the longitudinal experiment, epoch 6 started at global tick 19948 and ended at 23315. Its body lived approximately 3367 ticks, but `LivingBodyState.age_ticks` ended around 23314. Since canonical senescence begins at `senescence_start_ticks = 2048`, that body was treated as physiologically old almost from the beginning.

This contaminates:

- senescence;
- wear from senescence;
- age at death;
- any future physical capacity dependent on age;
- survival comparisons between morphologies.

Therefore, the observed duration results of crawler, asymmetric, and the return humanoid **are not yet clean evidence of morphological differences**.

---

## 2. Three Canonical Clocks

The system must distinguish three classes of time.

### 2.1 `symbiont_tick` — identity history

Conceptually equivalent to the current `OrganismRuntime._tick_count`.

Properties:

- monotonic during the entire continuity of the Symbiont;
- does not reset between bodies;
- does not produce senescence;
- does not determine physical growth;
- does not determine biological death;
- serves to order memory, experience, and causality.

Example:

```text
Symbiont #17
symbiont_tick:
0 -> 4513 -> 8922 -> 13323 -> 16775 -> 19948 -> 23315
```

Legitimate uses:

- timestamps of experiences;
- episode order;
- model creation/validation;
- support/recency of beliefs;
- embodiment history;
- cognitive structure;
- temporal causality;
- reproducibility.

### 2.2 `body_age_ticks` — local physiological age

It is a property of the current body.

Properties:

- starts at zero in a new body;
- increases exactly one tick while that body is alive;
- persists on `resume` of the same body;
- is never copied to a fresh body;
- controls physical ontogeny and senescence.

Example:

```text
symbiont_tick = 19948
new body
body_age_ticks = 0

...

symbiont_tick = 23315
body_age_ticks = 3367
```

### 2.3 Age/recency of cognitive structures

Concepts, sensors, edges, models, episodes, or hypotheses can maintain their own age or recency counters.

Examples:

- `edge.age_ticks`;
- `sensor.age_ticks`;
- `last_seen_tick`;
- `created_tick`;
- `last_validated_tick`;
- memory recency classes.

These counters describe the epistemological history or life of a structure. They do not represent the biological age of the Symbiont.

---

## 3. State Ownership

### 3.1 Exclusive Body State

The following fields belong to the physical body/embodiment:

- `energy_reserve`;
- `max_energy`;
- `structural_integrity`;
- `temperature`;
- `fatigue`;
- `growth_progress`;
- `senescence`;
- `body_age_ticks`;
- `vital_state`;
- damage/repair per structure;
- physiological state;
- physical death.

Death is irreversible **for that body**.

### 3.2 Exclusive Symbiont State

The persistent Symbiont possesses:

- `organism_id`;
- `symbiont_tick`;
- memory;
- experience;
- episodes;
- cognition;
- private models;
- beliefs;
- causal knowledge;
- history of embodiments;
- identity lineage.

It does not possess:

- youth;
- biological maturity;
- senescence;
- body age;
- body death.

### 3.3 Embodiment State

The link between a Symbiont and a Body possesses:

- `embodiment_epoch`;
- `body_kind`;
- opaque sensorimotor contract;
- `started_at_symbiont_tick`;
- `ended_at_symbiont_tick`;
- `body_age_ticks`;
- reacclimation state;
- active body schema;
- specific sensorimotor knowledge.

---

## 4. Canonical Lifecycle

### 4.1 Symbiont

```text
created
  -> active/embodied
  -> dormant
  -> active/embodied
  -> dormant
  -> ...
```

Valid execution states:

- `active`: running in a body;
- `dormant`: persisted identity without active execution;
- `suspended`: execution temporarily frozen with intent to continue.

The Symbiont does not go through:

```text
young -> mature -> senescent -> dead
```

as a consequence of time.

### 4.2 Body

```text
birth
 -> growth
 -> maturity
 -> senescence
 -> death
```

This lifecycle resets with each fresh body.

### 4.3 Re-embodiment

A dead body cannot `resume`.

```text
Body A DEAD
Symbiont DORMANT
      |
      v
fresh Body B age=0
Symbiont ACTIVE
embodiment_epoch += 1
```

---

## 5. Required Code Changes

### 5.1 `LivingBodyState`

Conceptual rename:

```text
age_ticks -> body_age_ticks
death_tick -> body_death_age_ticks
```

A physical rename migration can be done in a later version; v1 may preserve serialized keys for compatibility, but the semantics must be defined as **local to the body**.

Increment rule:

```python
self._tick_count += 1
if self._living_body_state.alive:
    self._living_body_state.advance_age()
```

Forbidden:

```python
body.age_ticks = symbiont_tick
```

### 5.2 `PhysiologyController`

Transitions must receive both global and local context only when necessary.

Physical death is recorded as:

```text
body_death_age_ticks
```

The global tick of death belongs to the epoch summary:

```text
ended_at_symbiont_tick
```

They must not merge into a single field.

### 5.3 `OntogenyController`

Must exclusively query:

- `body_age_ticks`;
- growth;
- energy;
- integrity;
- senescence;
- vital state.

Never:

- `symbiont_tick`;
- identity age;
- number of embodiments;
- amount of memory;
- cognitive experience.

### 5.4 `DevelopmentalTracker`

Must remain descriptive and cognitive, never biological.

States like:

```text
developing
consolidating
stable
reorganizing
```

are acceptable if they derive from cognitive evidence.

States like:

```text
young
adult
old
senescent
declining because age
```

are not acceptable as properties of the Symbiont.

The name `declining` must be audited: if it derives from load, stress, or structural health it can be kept as descriptive telemetry; if it derives from global age it must be removed or renamed.

---

## 6. Senescence

Senescence belongs exclusively to the Body.

Rule:

```text
if body_age_ticks >= senescence_start_ticks:
    apply body senescence
```

Never:

```text
if symbiont_tick >= senescence_start_ticks:
    apply senescence
```

Senescence can affect:

- physical repair;
- wear;
- motor capacity;
- metabolism;
- body reproduction.

It cannot directly affect:

- cognitive capacity;
- memory;
- plasticity;
- number of concepts;
- SLM;
- predictor budget.

Any future decrease in plasticity must be justified by:

- stability;
- uncertainty;
- resource pressure;
- structural saturation;
- lack of utility;
- contradictory evidence;

not by "Symbiont age".

---

## 7. Memory, Forgetting, and Passage of Time

The fact that the Symbiont does not age does not imply infinite memory.

Forgetting can derive from:

- bounded capacity;
- lack of use;
- interference;
- contradictory evidence;
- low utility;
- failed consolidation;
- computational pressure.

Time can participate in recency, but not as an aging mechanism.

Legitimate example:

```text
last_used_tick << current_tick
AND low_support
AND low_utility
=> candidate for retirement
```

Forbidden example:

```text
symbiont_tick > 50000
=> cognitive decay
```

---

## 8. Checkpoint Migration

### 8.1 Checkpoints with `embodiment_lifecycle`

For the current body:

```text
expected_body_age =
    saved_at_tick - embodiment_lifecycle.current.started_tick
```

If the checkpoint was produced by the contaminated implementation and:

```text
living_body.age_ticks ~= saved_at_tick
AND current.started_tick > 0
```

it must be migrated to:

```text
living_body.age_ticks = expected_body_age
```

An ambiguous checkpoint must not be silently migrated.

The migration must:

1. unequivocally detect the old pattern;
2. record migration version;
3. fail-closed if fields contradict each other;
4. not modify memory/cognition.

### 8.2 Legacy without embodiment lifecycle

For historical epoch 1:

- preserve `living_body.age_ticks`;
- verify it does not exceed `saved_at_tick`;
- create initial lifecycle with `started_tick = 0`.

Do not infer non-existent epochs.

---

## 9. Required Telemetry

Each Physics3D tick must be able to passively project:

```text
symbiont_tick
embodiment_epoch
body_age_ticks
body_vital_state
body_senescence
reacclimation_remaining
```

Observer-only.

The organism continues receiving only its opaque signals.

---

## 10. Mandatory Tests

### T1 — fresh body

```text
Symbiont tick 10_000
fresh body
=> body_age_ticks = 0
```

### T2 — independent advance

After 100 ticks:

```text
symbiont_tick = 10_100
body_age_ticks = 100
```

### T3 — resume

Stopping/resuming the same body preserves:

```text
body_age_ticks
senescence
growth
integrity
```

### T4 — re-embodiment

Switching to fresh body:

```text
body_age_ticks = 0
senescence = 0
growth = canonical fresh state
```

without modifying:

```text
organism_id
symbiont_tick
memory
experience
cognition
```

### T5 — senescence

Two Symbionts with different `symbiont_tick` but bodies of equal age must have the same constitutive senescence dynamics, all else being equal.

### T6 — death

`body_death_age_ticks` must be in local body coordinates.

The epoch must separately preserve:

```text
ended_at_symbiont_tick
```

### T7 — checkpoint migration

A known contaminated checkpoint must migrate deterministically and an ambiguous checkpoint must fail closed.

---

## 11. Acceptance Criteria

This spec is closed when:

1. no body obtains its age from the global tick;
2. senescence depends exclusively on body age;
3. an old Symbiont can receive a physiologically young body;
4. re-embodiment does neither rejuvenate nor age the Symbiont because the Symbiont does not possess biological age;
5. memory/cognition preserve global historical time;
6. telemetry distinguishes the two clocks;
7. tests prevent merging them again.

---

## 12. Scientific Consequence

The previous experiments H->H->H->C->A->H are useful as architecture discovery, but not as a clean survival comparison between bodies.

After implementing this separation the same protocol must be repeated before claiming survival or senescence differences by morphology.
