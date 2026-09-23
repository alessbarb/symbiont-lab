# Physics3D Telemetry v4 — Lossless Temporal Compaction

Status: canonical for new Physics3D runs.

## Goal

Preserve the complete observer-visible Physics3D evidence while making storage
scale with information change rather than with repeated full state.

Telemetry v4 is apparatus-owned and passive. The organism and runtime still
produce the complete completed-tick observation. Compaction happens only at the
persistence boundary and never feeds data back into Symbiont.

## Core invariant

For every recorded tick `T`:

```text
reconstruct(T) == original passive_telemetry_state(T)
```

and the reconstructed `Tick3D` summary is likewise exact.

No float quantization, sampling, threshold-based deletion, or arithmetic delta
accumulation is allowed.

## Run layout

```text
telemetry-v4/
└── <run-id>/
    ├── manifest.json
    ├── transitions.ndjson
    ├── anchors/
    │   └── tick-XXXXXXXXXXXX.json
    ├── objects/
    │   └── sha256/
    │       └── aa/<sha256>.json
    └── indexes/
        └── anchors.ndjson
```

Each execution creates one immutable run directory.

## Representation

### Anchors

The first recorded tick and every configured anchor interval contain complete
reconstruction state:

- exact rich observer state;
- exact compact Tick3D summary;
- optional organism + physical checkpoint payload supplied by the engine;
- transition-chain record hash;
- independent anchor SHA-256.

The default interval remains 1024 ticks.

### Transitions

Every completed cognitive tick has exactly one transition record.

After the first anchor, records contain exact sparse patches for:

- the rich observer state;
- the Tick3D summary.

Allowed operations are deliberately small:

```text
set     replace/create an exact JSON value
remove  remove an exact JSON member
ref     replace with an immutable content-addressed JSON subtree
```

Lists with stable length are diffed element by element, which keeps joint,
position and other fixed-shape arrays sparse. A list shape change falls back to
an exact replacement.

### Content-addressed objects

Large slow-changing subtrees can be stored under their canonical SHA-256 and
referenced by transitions. Initial preferred surfaces are:

```text
/observer_semantics
/cognitive_topology
/body_schema
/self_model
/sensorimotor/motor_primitives
```

This policy changes storage only. A reader always materializes the original
logical state.

## Exactness

Patches contain replacement values, never numeric increments such as
`x += delta`. This prevents cumulative floating-point drift.

Canonical JSON uses:

- sorted keys;
- compact separators;
- UTF-8;
- `allow_nan=False`.

The same canonical representation is used for content hashes.

## Integrity

`transitions.ndjson` remains a SHA-256 chain:

```text
record[n].previous_record_hash == record[n-1].record_hash
```

Verification additionally checks:

- sequence continuity;
- strictly increasing ticks;
- transition hashes;
- reconstructed state hashes;
- reconstructed summary hashes;
- anchor hashes;
- every referenced object hash;
- final manifest hash and clean closure.

Missing or tampered content fails closed.

## Reader API

```python
reader = TelemetryV4Reader(run)

reader.state_at(tick)
reader.iter_states()
reader.iter_summaries()
```

Compatibility helpers expose materialized lists where older studies still need
them:

```python
load_v4_transitions(run)
load_v4_tick_records(run)
```

`persistence.load_telemetry_records()` and
`persistence.load_telemetry_transitions()` auto-detect v4 and v3 so studies do
not depend on a physical telemetry version.

## Compatibility

Telemetry v3 remains readable and immutable. New Physics3D executions use v4.

Historical single-file telemetry remains readable for summary records, but it
cannot fabricate rich transition state that was never recorded.

## Separation of evidence and interpretation

v4 implements the lossless evidence layer:

```text
L0 anchors
L1 exact transitions
```

Future derived layers remain separate and regenerable:

```text
L2 episodes
L3 consolidated knowledge
```

Those layers may summarize or consolidate evidence, but they must never rewrite
L0/L1 or feed observer semantics back into the organism.

## Files

Implementation:

```text
src/symbiont_lab/physics3d/telemetry_compaction.py
src/symbiont_lab/physics3d/telemetry_v4.py
```

Telemetry v3 remains in `telemetry.py` for historical reads.

## Acceptance gates

The v4 core is accepted only if:

1. every generated state reconstructs exactly;
2. every generated Tick3D summary reconstructs exactly;
3. sync and async writers are semantically equivalent;
4. tampering or missing CAS content fails closed;
5. sparse-changing synthetic telemetry is smaller than repeated full-state JSON;
6. existing v3 readers and studies continue to work.
