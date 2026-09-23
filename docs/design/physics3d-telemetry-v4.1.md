# Physics3D Telemetry v4.1 — Typed Temporal Streams

Status: canonical writer for new Physics3D runs after cutover.

## Purpose

Telemetry v4.1 replaces generic recursive JSON patching with typed temporal
streams while preserving exact reconstruction of every completed cognitive tick.

The storage layer remains apparatus-owned and passive:

```text
runtime.step()
  -> passive_telemetry_state()
  -> telemetry encoder
  -> immutable evidence
```

Telemetry never feeds cognition, action selection, learning, or organism memory.

## Core invariant

For every committed tick `T`:

```python
canonical_json(reader.state_at(T)) == canonical_json(original_state_T)
canonical_json(reader.summary_at(T)) == canonical_json(original_Tick3D_T)
```

No sampling, float quantization, epsilon filtering, lossy compression, or
semantic deletion is permitted.

## Layout

```text
telemetry-v4.1/<run-id>/
  manifest.json
  ticks.ndjson

  schemas/
    frames.ndjson

  frames/
    dense.ndjson
    summary.ndjson
    fallback.ndjson

  structures/
    state.ndjson
    static.ndjson

  events/
    events.ndjson

  anchors/
    tick-XXXXXXXXXXXX.json

  checkpoints/
    tick-XXXXXXXXXXXX.json

  objects/
    sha256/aa/<hash>.json

  indexes/
    anchors.ndjson
```

## Temporal classes

### Dense channels

Frequently changing JSON shapes with mostly stable structure:

- `pre`
- `post`
- residual `runtime` state
- residual `cognition` state
- `action`
- `physics`
- `outcome`
- `timing_ms`
- optional `slm`
- optional `episodic_memory`

The first frame for a shape stores a full scalar vector. Later frames choose
between a full vector and a sparse `[index, value]` vector, whichever is
smaller. Field names and container topology are stored once in an immutable
frame schema.

### Structural channels

Long-lived state with stable entity identity:

- `cognitive_topology`
- `body_schema`
- `runtime.signal_knowledge`
- `runtime.sensory_phenotype`
- `self_model`
- residual `sensorimotor`

Lists containing stable IDs such as `node_id`, `primitive_id`,
`actuator_id`, `signal_id`, etc. are transformed into a reversible keyed
internal AST plus an explicit order vector. This keeps scalar evolution inside
existing entities from becoming list replacement.

The internal AST is tagged at every node, so arbitrary user/runtime JSON cannot
collide with telemetry markers.

### Events

Explicit event paths are removed from snapshot state and persisted once:

Ephemeral per-tick streams:

- `runtime.knowledge_events`
- `runtime.runtime_events`
- `runtime.experience_records_created`
- `cognition.mutations`
- `cognition.recycling_events`

Cumulative stream:

- `sensorimotor.episodes`

Cumulative events are emitted as append records while the current list is an
exact extension of the previous list. If the source ever rewrites history, the
writer emits an exact reset snapshot rather than assuming append-only behavior.

### Static objects

`observer_semantics` is content-addressed and emitted only when its canonical
hash changes.

Mutable topology/body-schema/self-model state is never admitted wholesale to
CAS.

### Exact fallback

Any path not covered by the declared layout remains in the v4.0 exact patch
engine. Unknown future runtime fields therefore remain reconstructible instead
of being silently discarded.

Fallback size and operation count are surfaced in the manifest and benchmark.

## Frame schemas

A frame schema stores container topology once and replaces every scalar leaf
with an integer slot.

Example logical value:

```json
{"position":[0.1,0.2,1.0],"alive":true}
```

becomes one immutable schema plus frames such as:

```json
{"t":100,"c":"pre","s":12,"m":"f","v":[0.1,0.2,1.0,true]}
```

or:

```json
{"t":101,"c":"pre","s":12,"m":"s","v":[[0,0.11],[1,0.21]]}
```

The sparse form is used only when its canonical JSON encoding is smaller.

Signed zero is compared via canonical JSON, so `0.0` and `-0.0` are not
compacted away as equal.

## Anchors and checkpoints

Anchors contain only reconstruction state:

- full logical state;
- full Tick3D summary;
- active schema IDs;
- stream offsets;
- tick-stream offset;
- committed tick hash.

Large organism/physical snapshots live under `checkpoints/` and are referenced
from tick commits. They are not embedded in anchors.

This prevents the former 15–20 MB organism checkpoint from inflating every
telemetry anchor.

## Tick commit protocol

All component streams are written first. The checkpoint and anchor, when due,
are written next. `ticks.ndjson` is appended last.

A commit contains:

- sequence and tick;
- previous commit hash;
- exact state SHA-256;
- exact summary SHA-256;
- per-stream emitted record hashes;
- per-stream end offsets;
- removed/present channels;
- optional checkpoint reference;
- anchor flag.

Only data reachable from the last valid tick commit is committed evidence.
Trailing stream bytes after a crash are uncommitted and ignored.

## Reader

`TelemetryV41Reader` supports:

```python
state_at(tick)
summary_at(tick)
iter_states(...)
iter_summaries(...)
iter_events(...)
```

Random access:

1. locate nearest anchor <= T;
2. prime stream decoders from anchor state and active schemas;
3. seek each stream to the anchor byte offset;
4. replay only committed ticks through T;
5. recompute and verify state/summary commitments.

Sequential iteration streams records with constant per-stream lookahead rather
than loading the full run into memory.

## Version-neutral API

All consumers should use:

```python
from symbiont_lab.physics3d.telemetry_reader import open_telemetry

reader = open_telemetry(path)
```

Supported:

- telemetry v3;
- telemetry v4.0;
- telemetry v4.1.

Historical summary-only NDJSON remains supported only through
`load_telemetry_records()` because rich state never existed there.

## Tooling

### Benchmark

```bash
symbiont-telemetry-benchmark RUN
symbiont-telemetry-benchmark RUN --compare OTHER_RUN
```

Reports:

- total bytes;
- evidence bytes excluding checkpoints;
- bytes/tick;
- canonical raw-state bytes;
- storage ratio;
- fallback bytes/fraction;
- stream breakdown;
- sampled `state_at` latency.

### Converter

```bash
symbiont-telemetry-convert OLD_RUN --output DESTINATION
```

The converter:

1. reads source state/summary through the neutral reader;
2. writes v4.1;
3. verifies v4.1 integrity;
4. re-reads source and destination;
5. compares canonical state and summary bytes for every tick.

The source is never modified.

## Acceptance gates

Before treating v4.1 as scientifically validated on the reference 4,781-tick
run:

- 100% state reconstruction equality;
- 100% Tick3D reconstruction equality;
- evidence storage < 200 MB excluding checkpoints;
- target 50–150 MB;
- fallback < 5% of evidence bytes;
- state_at p95 < 100 ms;
- no lost ticks;
- bounded async writer queue;
- v3/v4.0/v4.1 compatibility;
- primitive-effect study equivalence;
- full repository test suite green.

## Non-goals

v4.1 does not implement:

- lossy semantic forgetting;
- neural compression;
- float quantization;
- gzip/zstd/zip;
- Parquet/SQLite;
- binary XOR/varint encoding.

Those may be evaluated after structural redundancy has been removed and the
lossless typed-stream architecture has been validated on real runs.
