# World Ecology v1

Status: implemented; extended by `emergent-physical-affordances-v1.md`

## Goal

Move ecosystem behavior out of Pygame and into World so that visible ecological
change has causal consequences in the simulation.

This increment adds real, persistent, deterministic ecological state to
`DynamicGeography` and couples that state to resource renewal.

## Dynamic state

Each cell may now carry:

- `surface_water` — bounded physical water accumulation derived from moisture,
  permeability, elevation and neighboring runoff;
- `detritus` — bounded residual material deposited by observed organism death;
- `ecological_pressure` — bounded local pressure accumulated by repeated living
  presence;
- existing `traces` and `disturbance`.

All values are in `[0, 1]`.

## Surface water

Surface water is initialized deterministically from terrain:

```text
moisture
  × low-elevation preference
  × permeability
  → initial surface water
```

At every geography step, active water relaxes toward the terrain equilibrium,
undergoes temperature-dependent evaporation, and receives modest deterministic
downhill inflow from wetter/higher neighbors.

The state is persisted in checkpoints and participates in tick rollback.

## Death and detritus

A living→dead transition deposits detritus and local disturbance in the cell where
death was observed.

The death effect occurs inside the same `IntegratedWorldTickTransaction` as the
organism transition. If the tick aborts, detritus and disturbance roll back with
the rest of the universe.

World additionally emits an apparatus-side `ECOLOGY_CHANGED` event describing
the death-cell deposition.

## Ecological pressure

Every living occupant contributes local ecological pressure each tick. Pressure
decays when occupation ceases.

This represents persistent local load without assigning a semantic interpretation
such as trampling, grazing or pollution.

## Effective fertility

Base terrain fertility remains immutable ground-truth geography. Dynamic effective
fertility is derived from:

```text
base fertility
+ detritus contribution
+ surface-water contribution
- ecological pressure
- disturbance
```

The result is bounded to `[0, 1]`.

## Resource renewal

`WorldEnvironment.renew_resources()` now accepts a generic
`renewal_factor`. Positive resource recovery is scaled by the factor while
resource-law decay remains unchanged.

Population World computes:

```text
renewal_factor = 0.20 + 0.80 × effective_fertility
```

Thus local ecology changes the rate at which existing opaque resource pools
recover, without exposing human semantic resource labels to cognition.

## Constitution boundary

Ecology v1 changes causal World physics. The Genesis constitution therefore
changes its `interaction_rules_hash` to include `ecology-v1`.

A checkpoint created under the previous physics must not silently resume under
these rules when constitution verification is enabled.

## Observatory / Pygame

The read-only World snapshot now exposes evaluator-side:

- `effective_fertility`;
- `surface_water`;
- `detritus`;
- `ecological_pressure`.

Pygame renders those actual states. In particular, reflective water rendering no
longer infers water from moisture alone.

## Invariants

- deterministic for a fixed world seed and prior state;
- transaction rollback covers all ecological state;
- checkpoint roundtrip preserves ecology;
- no new organism action class is introduced;
- no semantic resource category is exposed to cognition;
- Pygame remains a passive consumer.
