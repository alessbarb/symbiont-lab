# P0 — Living Body

Status: **canonical implementation in progress — L1/L2/L3/L4 complete; L5 mechanism implemented, validation pending**.

This specification replaces the previous direction of adding cognitive or
locomotor machinery before physical closure. It also supersedes the old
canonical interpretation of reproduction as a consequence of cognitive
saturation or blocked structural growth.

## Three invariants

> **The genome defines capacities and physiological dynamics. It never defines
> behavioral solutions.**

> **The World provides opportunities and consequences. It never provides
> objectives.**

> **Cognition receives signals. It never receives their meaning.**

These are architecture invariants, not aspirations.

## Why P0 now

Current Physics3D results show that structural cognitive ecology can avoid
predictor monopoly, but the organism still lacks a single coherent living body.
The code currently contains overlapping physiological truths:

| Current component | Current authority | P0 decision |
| --- | --- | --- |
| `BodyPhysiology` | energy, integrity, temperature, alive | **remove as parallel truth** |
| `MetabolicLedger` | observation/cognition/persistence/maintenance reserve | **retain accounting mechanics, absorb into canonical physiology** |
| `HomeostaticController` | integrity, activity scale, plasticity, repair | **retain mechanisms, no independent state owner** |
| `PhysiologyController` | vital state/death | **retain transition rules, no independent state owner** |
| `DevelopmentalTracker` | cognitive-development telemetry | **retain as descriptive telemetry only; not biological maturity** |
| `OntogenyController` | growth, maturity, senescence, reproductive readiness | **canonical constitutive body mechanism** |
| Physics3D `PhysicalResource` | finite physical material | **retain world-side physical source** |

P0 must end with exactly one owner for persistent physiological state.

## Canonical boundary

```text
WORLD
    |
    | physics, matter, heat, contact, damage
    v
LIVING BODY
    |
    +-- reserve / matter
    +-- integrity / damage
    +-- temperature
    +-- fatigue / recoverability
    +-- repair
    +-- growth / age
    +-- reproductive capacity
    +-- vital state / death
    |
    | opaque interoceptive channels
    v
SYMBIONT COGNITION
    |
    +-- perception
    +-- memory
    +-- plasticity
    +-- prediction
    +-- spontaneous action
```

World truth never crosses the boundary as `food`, `resource`, `damage`,
`hunger`, `fitness`, `goal`, `repair-needed` or `reproduce`.

## P0.1 — one physiology

Introduce one organism-owned physiological state with, at minimum:

- finite assimilable reserve/material;
- structural integrity;
- body temperature;
- fatigue / available activity capacity;
- age/development state;
- irreversible vital state.

All physiological transitions operate on this state. `MetabolicLedger`,
homeostatic rules and vital-state transitions may survive as internal mechanisms
or views, but they may not own duplicate persistent state.

There must not be two independent energy values, two independent integrity
values or two independent alive/dead authorities.

### Migration rule

Do **not** add a fifth façade over the four existing systems. Move state
ownership first, then delete the old duplicate field/path.

## P0.2 — autonomous body homeostasis

Homeostasis is constitutive body dynamics, not a learned cognitive action.

Allowed innate mechanisms include:

- basal consumption;
- passive heat exchange;
- bounded thermoregulation;
- activity suppression when physiologically constrained;
- bounded tissue repair when material/energy is available;
- fatigue accumulation and recovery;
- irreversible death when physical viability is lost.

Cognition does not receive a reward for any of these and does not need to
discover the existence of wound healing before the body can repair itself.

Cognition may later learn regularities about the interoceptive consequences.

`runtime.repair(requested)` has been removed from the canonical runtime. Repair
is now constitutive body homeostasis and consumes maintenance reserve whenever
damaged tissue and resources coexist.

## P0.3 — multidimensional opaque interoception

Do not collapse body state into one somatic scalar.

The body exposes multiple opaque channels with stable ordinal identity. The
apparatus may know their physical source; cognition sees only anonymous signals.

Minimum physical dimensions for the first gate:

- reserve/material state;
- integrity;
- temperature;
- fatigue/activity capacity;
- one or more local stress/tension channels if physically available.

No channel carries a valence bit, desired setpoint, semantic label or action
recommendation.

The existing host-facing `internal.metabolic_reserve`,
`internal.integrity`, `internal.repair_pressure`, etc. are not the target
Physics3D contract because their names encode evaluator semantics. The physical
body must transduce them through opaque receptor ordinals.

## P0.4 — closed physical energy/material loop

Physics3D already contains a useful partial mechanism:

```text
finite PhysicalResource
    -> physical contact
    -> bounded offered material
    -> organism absorption
    -> source depletion
```

P0 preserves this and removes the remaining conceptual split.

Required invariants:

1. no reserve increase without a physical transfer;
2. material removed from World equals material accepted by Body;
3. a full/dead/incompatible body cannot consume material;
4. no cognitive performance, prediction score or evaluator metric mints reserve;
5. the World does not select an internal metabolic compartment;
6. all long-run survival must close through this physical loop.

The isotropic field may exist as physics, but its organism-facing signal must
remain an opaque local measurement and must not encode direction or identity.

## P0.5 — one physical cost economy

Movement, sensing, computation, persistence, repair, growth and reproduction
ultimately draw from the same finite organism-owned matter/energy economy.

Internal accounting categories may exist to model conversion constraints, but
they must not behave as independent currencies that can become replenished
without material conservation.

Measured mechanical work remains a legitimate apparatus-to-body cost because it
is a physical consequence, not a reward.

## P0.6 — reproduction is physiology, not cognitive saturation

The canonical path must remove this condition:

```text
adaptive
AND capacity_exhausted
AND blocked_growth
=> reproductive readiness
```

Cognitive saturation is neither fertility nor reproductive motivation.

First Living Body reproduction may be simple and asexual, but readiness must
derive only from constitutive and physiological state, for example:

- developmental maturity;
- sufficient reserve/material;
- sufficient integrity;
- non-terminal physiological state.

Starting reproduction consumes real parental reserve/material. World may deny
materialization because physical space/material is unavailable, but it may not
create readiness.

No semantic `REPRODUCE` reward or evaluator instruction enters cognition.

## P0.7 — ontogeny

The first implementation needs no embryology.

Use a continuous physical lifecycle:

```text
birth -> growth -> maturity -> senescence -> death
```

Age changes physical capacity/rates, not learned solutions. Candidate
constitutional effects include body scale, reserve capacity, repair rate,
thermal range, fatigue recovery and reproductive capacity.

Acquired cognitive state is not copied into a descendant.

## P0.8 — reduce motor scientific scaffolding

Spontaneous motor activity is constitutionally acceptable.

The canonical organism must not depend on a pre-written scientist protocol that
guarantees:

- actuator coverage;
- scheduled null experiments;
- hypothesis retesting;
- verification epochs;
- a fixed number of hypothesis retries.

Those mechanisms may remain temporarily in Lab as experimental comparators, but
must not be claimed as organism-discovered behavior.

P0 does **not** require solving motor learning. It requires that the body can
produce spontaneous action and experience its physical/interoceptive
consequences.

## P0.9 — no reward

There is no scalar reward for:

- survival;
- approaching or touching material;
- absorption;
- repair;
- locomotion;
- reproduction;
- prediction accuracy.

The causal loop is sufficient:

```text
action
  -> external physical change
  -> internal physiological change
  -> opaque perception
  -> later action
```

Evaluator metrics may measure this loop but never enter it.

## Implementation order

### L0 — stop adding top-down intelligence

Until Living Body passes its gate, defer:

- locomotion optimization;
- planners;
- intrinsic-motivation reward proxies;
- automatic temporal-model promotion;
- RSSM / exact CTW work;
- higher-level reproductive strategy.

### L1 — state-owner audit and cutover

1. enumerate every persistent physiological field;
2. choose the single canonical owner;
3. migrate checkpoint schema;
4. delete duplicate Body/runtime state;
5. add equality/invariant tests proving no second truth remains.

### L2 — physical homeostasis

1. basal cost;
2. autonomous bounded repair;
3. fatigue/recovery;
4. temperature dynamics/regulation;
5. activity capacity derived from physiology;
6. irreversible vital transition.

### L3 — opaque body interoception — implemented

The canonical Physics3D surface now separates physical sensing from
physiological transduction:

```text
PyBullet anthropomorphic-v4 body physics
  -> rec.0 ... rec.102

LivingBodyState
  -> apparatus-only four-source transducer
  -> rec.103 ... rec.106
```

The four physiological sources are sampled independently from the single
canonical body state.  Their human meaning exists only inside the apparatus.
The serialized mapping contains only source ordinals by opaque slot.

Fifteen local contact-load channels complement fifteen contact-presence
channels and are derived from measured normal force, not from a semantic
damage or pain flag.

Unit contracts cover independent variation, opaque label permutation,
ordinal-only checkpoint/restore and independent local contact loads.

### L4 — conservation — complete

Physical energy now has one spendable owner:

```text
external physical transfer
    -> LivingBodyState.energy_reserve
    -> sensing / cognition / persistence / repair / mechanical-work cost
    -> depletion
```

`metabolic_reserve[observation/cognition/persistence/maintenance]` remains as
bounded functional accounting only. These balances may classify where cost was
incurred or restore accounting headroom, but they cannot mint physical energy
and they no longer determine viability independently.

Physics3D starts a fresh L4 subject with one energy capacity equal to the sum of
its declared metabolic accounting capacities. Accepted material increases that
pool once; `PhysicalResource` loses exactly the accepted amount. Repair is
bounded by both maintenance accounting availability and the common physical
pool. A dead runtime cannot absorb material.

Validated mechanical gates:

```text
Physics3D: world_loss == accepted_body_gain
Clean World: world_loss == absorbed_transfer
Clean Body: energy_end == energy_start + absorbed - motor_cost - basal_cost
no_source -> no_long_run_gain
dead_body -> zero_gain
all cost kinds -> same energy_reserve
repair <= physical energy available
```

External environmental renewal is treated as an explicit world-side source term,
not organism replenishment. `SharedHabitat` resource units may use a declared
conversion factor (`physiological_usefulness`) and therefore are not assumed to
be numerically identical to body-energy units; conservation claims are made only
where the boundary contract defines common scalar units.

L4 validation complete. The canonical L1-L4 regression battery passed **193 tests**.
The subsequent adversarial conservation battery passed **42 tests**, including
the strengthened non-vacuous Clean World transfer gate. No remaining canonical
path was found that can increase body energy without an explicit physical
transfer.

### L5 — ontogeny and reproduction — mechanism implemented, validation pending

The canonical body now owns continuous ontogeny:

```text
birth
  -> energy-backed growth
  -> physical maturity
  -> age-driven senescence
  -> irreversible death
```

`LivingBodyState` owns `growth_progress` and `senescence`. The
`OntogenyController` derives life stage and reproductive readiness only from
body state and immutable physiology configuration. It does not inspect
cognitive topology, prediction quality, sensor count, action experience,
adaptation scores or evaluator state.

Growth consumes the same physical `energy_reserve` used by maintenance,
cognition and movement. Senescence begins only after constitutional age and
adds constitutive structural wear.

The old `ReproductivePressure` / blocked-cognitive-growth stack has been
removed from the canonical core. `HabitatBirthAuthority` now allocates only
identity, lineage and carrying-capacity slots; it owns no resource currency.

`SharedHabitat` now keeps carrying-capacity membership separate from its
physical resource stock. Admission and release change population occupancy only;
`consume()` is the operation that depletes resources, while `renew()` is an
explicit world-side source. Death therefore cannot regenerate physical material
through bookkeeping.

Asexual birth is conservative at the organism boundary:

```text
parent energy before
    = parent energy after
    + child initial energy
```

The child starts physically immature and cognitively germinal. Acquired
cognitive state is not copied. A denied birth consumes no parental energy.

Physics3D is constitution `genome_symbiont_physics3d_v9` with the
31-DoF `anthropomorphic-v4` body. Earlier Physics3D subjects must start fresh:
body-state schema v4 deliberately fails closed rather than adapting the old
14-DoF constitution.


### Hard anatomical constraints — implemented

Physics3D no longer emulates anatomical joint stops with controller-side spring
torques. The canonical humanoid is generated as a URDF from the private lab
constitution and loaded by Bullet with hard `lower`/`upper`, `effort`,
`velocity` and passive `damping` constraints for all 31 joints. The organism
still receives only opaque receptor/effector ordinals; anatomical labels remain
apparatus-only. Dynamic regression now excites the complete motor surface and
fails if any joint crosses its declared range by more than solver tolerance.

### L6 — return to behavior

Only after physical closure do we return to motor learning and ask what the
organism discovers. Walking is not a gate.

## P0 acceptance gate

A fresh subject must be able to run from birth without semantic intervention and
demonstrate all of the following in preregistered studies:

1. basal activity depletes finite reserves;
2. damage changes canonical body state;
3. repair occurs autonomously only when physically affordable;
4. internal channels change independently and remain opaque;
5. physical contact transfers conserved material from World to Body;
6. loss of all usable material eventually causes irreversible death;
7. material acquisition can prolong life without evaluator reward;
8. checkpoint/restore preserves the same physiological trajectory;
9. cognition ON/OFF does not change constitutive homeostatic laws;
10. no reproduction readiness field depends on cognitive topology, adaptation
    score or blocked growth.

Until these pass, claims about autonomous locomotion, survival strategy or
reproductive strategy are premature.

## Current-code findings motivating this spec

As of the P0 audit:

- `LivingBodyState` is now the single persistent owner for energy, integrity,
  temperature, fatigue, age, vital state and metabolic reserve dictionaries;
- `MetabolicLedger`, `HomeostaticController` and `PhysiologyController` now
  operate over that shared state;
- repair is constitutive and resource-backed; explicit `runtime.repair()` and
  apparatus-driven repair reflexes have been removed;
- Physics3D keeps the host `InteroceptionProvider` disabled and now exposes
  four independent `LivingBodyState` dimensions through opaque ordinal
  receptors: reserve ratio, structural integrity, temperature and fatigue;
- fifteen local somatic-load channels are derived directly from PyBullet
  contact force, paired with fifteen independent contact-presence channels;
- anthropomorphic-v4 exposes 31 motor DoF, 62 paired opaque effector ports,
  103 physical receptors and four opaque interoceptive receptors;
- the complete Physics3D sensory contract is 107 opaque `rec.N` slots and its
  cognitive sense-node capacity is 128, so the apparatus does not silently
  truncate the body surface;
- the apparatus-side interoceptive source-to-slot mapping is checkpointed only
  as ordinal permutation data; physiology labels are not serialized into the
  organism-facing sensory contract;
- Physics3D now couples finite material, accepted-transfer depletion, measured
  mechanical work, cognition, persistence and constitutive repair to the same
  physical `energy_reserve`;
- `LivingBodyState` now also owns `growth_progress` and `senescence`;
- `OntogenyController` implements energy-backed growth, body-derived maturity,
  senescence and physiological reproductive readiness without cognitive input;
- the legacy `ReproductivePressure` module and paired/clonal helper stack have
  been removed from the core;
- `HabitatBirthAuthority` is capacity/identity/lineage only and carries no
  parallel physical resource budget;
- successful asexual materialization transfers physical energy from parent to
  child exactly once; denied birth leaves parent energy unchanged.

These are code facts, not inferred biological claims.
