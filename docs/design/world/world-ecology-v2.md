---
id: design.world.world-ecology-v2
title: "World Ecology V2"
document_type: design
domain: world
status: active
canonical: true
implementation_status: implemented
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# World Ecology v2

Status: implemented core corrections; viability characterization available.

## Purpose

World Ecology v2 removes two apparatus artefacts discovered during the first
persistent eight-founder run:

1. clean founders shared the same internal cognitive RNG seed;
2. resource renewal advanced from inside the organism loop instead of from the
   World clock.

The goal is not to make Symbionts survive. The goal is to make survival or
death a consequence of physical trajectories in a reproducible ecosystem.

## Invariant 1 — founder stochastic independence

For canonical clean World, the internal Symbiont RNG seed is derived from:

```text
derive_world_seed(world_seed, "symbiont.cognitive:" + organism_id)
```

Therefore:

```text
same world_seed + same organism_id
    -> same RNG stream

same world_seed + different organism_id
    -> distinct RNG streams
```

No personality, goal, preference or strategy is injected. Only accidental
shared randomness is removed.

## Invariant 2 — ecology advances on the World clock

Resource renewal is a World process.

Every topology cell receives exactly one renewal step per World tick:

```text
for each world tick:
    propagate fields once
    renew each cell once
    process organisms
    resolve movement
    advance dynamic geography
```

Renewal count is therefore independent of:
- number of living organisms;
- local population density;
- organism processing order.

Population density may still affect ecology only through explicit physical laws
such as ecological pressure, traces, disturbance or hazards.

## Passive physiological accounting

Canonical clean World emits one observer-side `PHYSIOLOGY_BALANCE` event per
living founder tick.

The event reports:

```text
energy_start
energy_end
absorbed
motor_cost
basal_cost

integrity_start
integrity_end
basal_wear
deferred_damage
hazard_damage

alive
death_cause
```

The accounting identities are:

```text
energy_end
  = energy_start
  + absorbed
  - motor_cost
  - basal_cost
```

and

```text
integrity_end
  = integrity_start
  - basal_wear
  - deferred_damage
  - hazard_damage
```

These events are apparatus/observer data only and never enter Symbiont
cognition.

Terminal cause is derived only from physical state:
- `energy_depletion`;
- `structural_failure`;
- fallback `nonviable`.

## Genesis viability characterization

Protocol:

`world.genesis-viability-characterization`

Default pilot:
- 10 preregistered seeds;
- 8 founders;
- 600 ticks;
- 8x8 smoke topology.

It reports:
- lifespan distribution;
- extinction tick;
- survivor fraction;
- material absorbed;
- motor/basal cost;
- structural wear and damage;
- hazard exposures;
- movement count;
- final dispersion;
- births if any occur.

There is deliberately no pass/fail rule requiring survival.

The campaign is descriptive. It must not be used as an optimization target for
World parameters.

## Constitutional change

These changes alter causal experiment mechanics.

Genesis therefore uses:
- `ecology-v2` in `interaction_rules_hash`;
- `founder-rng-v2` in `interaction_rules_hash`;
- `rng_scheme_version = 2`.

Old checkpoints must not silently resume under Ecology v2 when constitution
verification is enabled.

## Not changed in this increment

World Ecology v2 does **not** yet tune:
- basal metabolism;
- effector cost;
- degradation rate;
- hazard probability;
- resource capacity;
- resource renewal rates;
- material exchange rate.

Those parameters should only be reconsidered after running the viability
characterization and inspecting the physical balance data.

## Next scientific step

Repeat the observed eight-founder scenario under Ecology v2.

The first question is not “did they survive?” but:

> Which physical term dominates each death, and how much population divergence
> appears once the accidental shared RNG is removed?

Only after that measurement should niche structure, material affordances or
hazard calibration be changed.
