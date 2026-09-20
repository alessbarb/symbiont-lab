# Hazard Ecology v2

Status: implemented.

## Why

The first eight-founder Ecology v2 run showed that structural failure, not
energy depletion, dominated mortality. Two apparatus artefacts were identified:

1. the so-called cyclical hazard was actually time-invariant;
2. density-dependent risk counted occupancy rather than living neighbours,
   so dead bodies could continue contributing to density.

Hazard Ecology v2 changes the physical World, not Symbiont cognition.

## Invariants

### Temporal structure

The cyclical hazard now uses a periodic exposure law with real zero-risk
troughs and high-risk peaks.

Canonical neutral-patch parameters:

```text
base_probability = 0.006
temporal_amplitude = 1.0
period = 160 ticks
```

At neutral density:

```text
tick   0 -> 0.006
tick  40 -> 0.012
tick 120 -> 0.000
```

No phase, period or hazard meaning is exposed to the organism.

### Spatial structure

Genesis uses persistent 4x4 apparatus-side habitat patches:

```text
sheltered
neutral
exposed
```

These names exist only in Lab ground truth. Symbionts receive ordinary opaque
physical observations.

Cyclical and density-related hazard laws differ by patch, so movement can alter
future physical risk without the World prescribing where an organism should go.

### Living density

Density-dependent hazard exposure uses only living neighbours.

A dead body:
- remains available as historical placement;
- contributes detritus through DynamicGeography;
- does not count as a living neighbour;
- is removed from the live OccupancyGrid.

This separates biological density from corpse/ecological residue.

### Density-coupled risk

The isolated baseline is deliberately small and risk grows with crowding.

Neutral-patch canonical law:

```text
base_probability = 0.0015
density_coupling = 20.0

density 0.0 -> 0.0015
density 0.2 -> 0.0075
density 1.0 -> 0.0315
```

The aim is not guaranteed survival. It is to make density risk physically
avoidable rather than an almost universal background death process.

## Persistence

The World environment now persists its hazard clock. Persistence schema is v5.
Restarting a checkpoint preserves the phase of temporal hazards.

Because this changes causal World mechanics, old Ecology v2 checkpoints are not
compatible with Hazard Ecology v2 and should not be silently resumed.

## Constitution

The World fingerprint now includes:
- temporal hazard-law parameters;
- regional hazard overrides;
- `hazard-ecology-v2`;
- `living-density-v1`;
- `hazard-patches-4x4-v1`.

## What did not change

No Symbiont code was changed.

The following remain untouched:
- metabolism;
- energy capacity;
- motor cost;
- basal structural wear;
- learning;
- AgencyModel;
- BodySchema;
- reproduction;
- resource abundance.

## Next experiment

Start a fresh eight-founder Genesis under the new constitution and compare:

- lifespan distribution;
- structural vs energetic death;
- hazard hits split by hazard;
- mean living density at exposure;
- occupancy of sheltered/neutral/exposed patches;
- dispersion;
- reproduction and lineage persistence.

No pass/fail target should require survival.
