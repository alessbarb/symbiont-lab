---
id: design.telemetry.physics3d-telemetry-v3
title: "Physics3d Telemetry V3"
document_type: design
domain: telemetry
status: superseded
canonical: false
implementation_status: historical
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Physics3D Telemetry v3

Status: canonical for new Physics3D runs.

## Goal

Preserve enough passive evidence to reconstruct what the Symbiont perceived,
what cognition produced, what action was requested/delivered, what the physical
body did, and what changed in learning state. Telemetry is apparatus-owned and
never feeds back into cognition.

## Run layout

```text
telemetry-v3/
└── <run-id>/
    ├── manifest.json
    ├── ticks.ndjson
    ├── deltas.ndjson
    └── snapshots/
        └── tick-XXXXXXXXXXXX.json
```

Each execution creates an immutable run directory. Runs are not concatenated.

## manifest.json

The manifest records:

- schema version and run id;
- organism id;
- UTC start/end timestamps;
- start/end ticks;
- seed;
- physics and cognition frequencies;
- substeps per cognitive tick;
- embodiment mode;
- effective configuration and SHA-256 fingerprint;
- software identity and SHA-256 fingerprint;
- snapshot interval;
- record/delta/snapshot counts;
- final tick-chain hash.

An unclosed run is incomplete even when its available tick chain is internally
valid.

## ticks.ndjson

One envelope per completed cognitive tick.

Each envelope contains:

- monotonic sequence number;
- organism tick;
- previous record hash;
- SHA-256 record hash;
- the compact `Tick3D` summary;
- a rich transition snapshot.

The rich transition is explicitly split into:

```text
pre -> runtime/cognition -> action -> physics -> post
```

### pre

- complete pre-tick physical pose;
- resource field/state;
- metabolic reserves/capacity;
- exact opaque receptor values actually delivered by `PhysicsReadingProvider`;
- sample monotonic timestamp.

No second evaluator-side sampling is performed.

### runtime

- transduced percepts;
- attention allocations;
- investigated capability/evidence count;
- signal knowledge;
- knowledge events;
- signal references;
- assimilation;
- homeostasis;
- developmental state;
- sensory phenotype;
- runtime lifecycle events;
- motor intents;
- newly created private `ExperienceRecord` payloads.

### cognition

- node activations;
- core/motor/primitive readouts;
- individual prediction errors with predictor id, target id, raw error and loss;
- structural mutations;
- topology revision and health;
- safety/frozen/recovery state;
- recycling and stranded concepts;
- predictive gain;
- active concepts;
- retiring predictors;
- structural contention/candidate metrics;
- representation maturity.

### action

For every delivered actuation:

- opaque actuator id;
- mapped opaque physical effector id;
- requested activation;
- delivered activation;
- actuator cost;
- health at execution;
- motor origin and origin detail.

### physics

Always recorded:

- number of physics substeps;
- mechanical work;
- body path length during the cognitive tick;
- resource contact;
- final contact count;
- maximum normal force;
- accumulated normal impulse;
- full final contact records including positions, normal, force and friction.

With `--telemetry-physics-trace`, every physics substep is also retained:

- base pose;
- linear/angular velocity;
- all motor joint positions/velocities/commanded torques;
- all contacts and forces.

This is high-volume diagnostic telemetry and is opt-in.

### post

- complete post-tick physical state;
- resource distance/remaining/absorbed energy;
- complete metabolic reserves/capacity;
- physiology state.

### body_schema

The actual BodySchema representation discovered by the organism at that tick.
It is never replaced with apparatus anatomy.

### sensorimotor

- exploration coverage;
- learned patterns;
- primitives/hypotheses;
- cognitive primitives;
- active investigation;
- controllability/directional consistency;
- replay state;
- multi-horizon sample counts;
- passive baseline samples;
- active opaque motor repertoire.

## deltas.ndjson

This stream contains structural changes only. Continuous activations/readouts
remain in `ticks.ndjson` and are not duplicated.

Delta surfaces are:

- cognition structure/recovery/lifecycle;
- BodySchema;
- sensorimotor repertoire/primitives/hypotheses.

Each delta stores the projected component state plus its SHA-256 digest.

## snapshots/

A complete snapshot is written on the first recorded tick and then every 1024
ticks by default.

It contains:

- full canonical organism checkpoint;
- full passive physical state;
- tick-chain record hash;
- independent snapshot SHA-256.

These snapshots provide reconstruction anchors without duplicating the full
organism checkpoint on every tick.

## Integrity

`ticks.ndjson` is a SHA-256 chain:

```text
record[n].previous_record_hash == record[n-1].record_hash
```

Verification also checks:

- sequence continuity;
- strictly increasing ticks;
- every record hash;
- final manifest hash;
- every snapshot hash;
- clean run closure.

Telemetry v3 must not silently skip corrupt records. Historical NDJSON may still
be opened as archived evidence, but canonical v3 replay verifies integrity.

## Analysis principle

Raw observation and derived interpretation are separate.

Telemetry v3 stores observation. Event detectors, causal candidates, statistical
summaries and scientific classifications should be generated later from the
immutable run and versioned independently. This allows the same run to be
reanalyzed with improved methods without rewriting experimental evidence.


## Primitive episode provenance

Telemetry v3 may include sensorimotor.episodes in the rich transition. These
records correlate an organism-discovered opaque motor episode with its exact tick
interval and independent evidence blocks. They carry no physical classification
and do not feed back into the organism.

Observer-side physical-effect studies may join this provenance with immutable
pre.physical, physics and summary records. Derived classifications remain
outside telemetry and outside the Symbiont checkpoint.
