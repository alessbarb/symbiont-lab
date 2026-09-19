# Emergent Physical Affordances v1

Status: implemented candidate

## Purpose

Allow Symbionts to discover how their bodies can alter the World without adding
semantic actions such as `dig`, `build`, `irrigate`, `fertilize` or
`move_material`.

The organism keeps the same primitive motor body. Meaning must arise from learned
causal relationships between opaque actuator channels and later perceptual change.

## Core rule

```text
opaque motor channel
      ↓
body-delivered physical impulse
      ↓
World mechanics
      ↓
possible locomotion + substrate change
      ↓
next-tick opaque local perception
      ↓
existing motor causal-discovery machinery
```

There is no action-specific reward and no privileged success signal.

## Motor surface

The default body still exposes the same six opaque actuator slots used by the
directional World binding.

No new `WorldAction` field is introduced. In particular there is no:

- dig;
- build;
- clear;
- irrigate;
- fertilize;
- move material.

The apparatus knows that a given slot maps to a physical direction. Cognition sees
only actuator IDs, requested/delivered activation and subsequent sensory
consequences.

## Primitive substrate impulse

Every delivered directional actuation produces a local substrate impulse before
World decides whether the body itself can move.

Therefore an actuator may:

- move the organism and alter substrate;
- fail to move the organism but still alter substrate;
- hit a boundary and only disturb the origin;
- compete with another body for movement while still having already exerted a
  physical impulse.

This deliberately separates **motor consequence** from **locomotion success**.

The impulse can redistribute existing:

- surface water;
- detritus;

and add local disturbance.

Transfer magnitude depends only on delivered activation and local physical
properties such as elevation/permeability.

## What the organism can perceive

Only three new local physical quantities are exposed to organism perception:

- local surface-water magnitude;
- local detritus magnitude;
- local disturbance magnitude.

Their apparatus labels are converted through `opaque_signal_id(...)`; the
organism receives only stable 16-character opaque IDs.

The following evaluator-side variables are deliberately **not** exposed:

- effective fertility;
- ecological pressure;
- effective permeability.

Those are latent World mechanics. If they matter, the organism must infer their
consequences indirectly through resource dynamics, movement success and other
ordinary perception.

## Delayed causal discovery

The existing motor-discovery system already compares percepts before actuation
with percepts from the next biological cycle and excludes proprioceptive echo
channels from causal evidence.

Physical affordance discovery therefore uses the existing machinery:

```text
tick N
  probe actuator A
  World applies physical consequences

tick N+1
  observe opaque local signals
  compare with pre-actuation percepts
  accumulate causal evidence for A
```

No World event is fed to cognition.

`SUBSTRATE_IMPULSE` exists only in the apparatus event journal for scientific
audit and replay.

## Emergent paths and barriers

Dynamic traversability is derived from:

```text
base permeability
+ disturbance contribution
- detritus loading
- surface-water loading
```

This means repeated primitive action can accidentally change what is traversable:

- repeated disturbance may open a previously marginal passage;
- accumulated detritus may close it;
- moving detritus elsewhere may reopen it;
- water redistribution can alter local resistance.

The organism is never told that it has "opened", "closed", "built" or "destroyed"
anything.

It can only discover stable action→world→future-action regularities.

## Scientific boundary

Observatory may see:

- substrate impulse events;
- transferred amounts;
- effective permeability;
- latent ecological variables.

Pygame may render the resulting physical state.

The organism may not receive those apparatus interpretations.

## Constitution

This changes causal World physics, so the Genesis interaction fingerprint includes
`physical-affordances-v1`.

Constitution-verified persistent worlds created before this rule set cannot resume
silently under the new mechanics.

## Validation

Tests cover:

- directional water/detritus redistribution;
- boundary impulses without fabricated transfer;
- transaction rollback;
- opaque signal identity;
- next-observation causal change;
- no semantic additions to `WorldAction`;
- dynamic opening/closing of traversal;
- apparatus-only `SUBSTRATE_IMPULSE` event emission.
