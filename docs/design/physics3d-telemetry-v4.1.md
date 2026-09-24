# Physics3D Telemetry v4.1 — Typed Temporal Streams

Status: canonical writer for new Physics3D runs. Revision 4 is active; v4.0 remains readable and available for rollback/compatibility.

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
    strings.bin
    frames.bin
    structural-paths.bin

  frames/
    dense.bin
    summary.bin
    fallback.bin

  structures/
    state.bin
    static.bin

  events/
    events.bin

  anchors/
    tick-XXXXXXXXXXXX.json

  checkpoints/
    organism/
      tick-XXXXXXXXXXXX.json
    physical/
      tick-XXXXXXXXXXXX.json
    extra/
      tick-XXXXXXXXXXXX.json

  objects/
    sha256/aa/<hash>.json

  indexes/
    anchors.ndjson
    ticks.ndjson
    events.ndjson
    structures.ndjson
```

## Temporal classes

### Dense channels

Frequently changing JSON shapes with mostly stable structure:

- `pre.physical`
- `post.physical`
- residual `pre` / `post`
- `physics.raw_substeps`
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
- `runtime.narrative`
- `runtime.signal_references`
- `self_model`
- residual `sensorimotor`

Lists containing stable IDs such as `node_id`, `primitive_id`,
`actuator_id`, `signal_id`, etc. are transformed into a reversible keyed
internal AST plus an explicit order vector. Cognitive edges without their own
ID use an observer-only composite identity derived from
`(source_id, target_id, kind, delay_ticks)` when that tuple is unique.
Revision 3 stores keyed entities as maps and emits only path-level `set/remove`
deltas. Profiles use `signal_id`; signal-knowledge claims use `claim_id`; edges
without their own ID use the observer-only composite identity above. The
independent order vector preserves the exact original list order. This prevents
claim/profile growth from creating a new whole-tree structural schema.

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

Ephemeral events are grouped into one record per channel/tick. Cumulative events
are emitted as `append_many` batches while the current list is an exact extension
of the previous list. If the source ever rewrites history, the writer emits an
exact reset snapshot rather than assuming append-only behavior.

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

A third exact frame mode, `copy`, is available for cross-channel temporal
identity. In particular, when and only when canonical bytes prove that

```text
pre.physical[t] == post.physical[t-1]
```

the writer stores a reference to the previous post-physics channel instead of
repeating the values. No continuity assumption is made.

Signed zero is compared via canonical JSON, so `0.0` and `-0.0` are not
compacted away as equal.

## Revision 4 binary encoding

Revision 4 changes physical representation only. Temporal semantics, evidence,
state hashes and observer ownership remain unchanged.

Binary streams are length-prefixed records. Values use explicit type tags:

- null / booleans as one-byte tags;
- integers as lossless signed varints;
- floats as exact IEEE-754 binary64, preserving signed zero;
- strings as IDs into one append-only UTF-8 dictionary;
- lists and mappings as typed containers;
- mapping keys are also dictionary IDs.

Dense frame schemas and structural paths are stored once using the same string
dictionary. Binary record SHA-256 values are committed by the existing tick
commit chain. Manifest, tick commits, anchors and derivative indexes remain
human-readable JSON.

This is not compression in the gzip/zstd sense and does not alter information:
the gain comes from storing repeated field names, signal IDs, claim IDs and
tokens once instead of on every JSON record.

## Anchors and checkpoints

Anchors contain only reconstruction state:

- full logical state;
- full Tick3D summary;
- active schema IDs;
- stream offsets;
- tick-stream offset;
- committed tick hash.

Telemetry anchors and large checkpoints have independent cadences. Revision 4
defaults to lightweight anchors every 256 ticks and large checkpoints every
1,024 ticks.

Large organism and physical snapshots live independently under
`checkpoints/organism/` and `checkpoints/physical/`. Additional apparatus
snapshot material, if any, is isolated under `checkpoints/extra/`. Tick commits
reference each component by path and SHA-256. Checkpoints are not embedded in
anchors.

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

After a successful tick commit, derivative indexes are appended for tick,
event-stream, and structural-stream offsets. These indexes are accelerators
only: they are never canonical evidence, and a missing or incomplete index
must not make committed evidence disappear.

## Reader

`TelemetryV41Reader` supports:

```python
state_at(tick)
summary_at(tick)
iter_records(...)
iter_states(...)
iter_summaries(...)
iter_events(...)
```

Random access:

1. locate nearest anchor <= T through the derivative anchor index; validate the
   selected anchor and fall back to a full anchor scan if the index is missing
   or corrupt;
2. prime stream decoders from anchor state and active schemas;
3. seek each stream to the anchor byte offset;
4. replay only committed ticks through T;
5. recompute and verify state/summary commitments.

Sequential iteration streams records with constant per-stream lookahead rather
than loading the full run into memory.

## Layout revisions

The physical schema version remains `4.1`, while the manifest carries a
`layout_revision`.

- revision 1 is the initial v4.1 layout that grouped `pre`, `post`, and
  `runtime` more coarsely;
- revision 2 introduced nested physical streams, narrative/signal-reference
  structural channels, cross-tick copy frames, split checkpoints, and indexes;
- revision 3 replaces whole-tree structural frame schemas with keyed path-deltas,
  adds `claim_id` identity for signal-knowledge claims, and batches events per
  channel/tick;
- revision 4 preserves revision 3 semantics but replaces verbose JSON payload
  streams with exact typed binary records: a global string dictionary, unsigned/
  signed varints, IEEE-754 float64, binary frame schemas and path IDs. Revision 4
  is the current experimental candidate.

Readers treat a v4.1 manifest with no `layout_revision` as revision 1. This
preserves readability of runs produced during the initial v4.1 rollout without
mutating historical evidence.

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
symbiont-telemetry-benchmark RUN --gate --expected-ticks 4781
```

Reports:

- total bytes;
- evidence bytes excluding checkpoints;
- bytes/tick;
- canonical raw-state bytes;
- storage ratio;
- fallback bytes/fraction;
- stream breakdown;
- sampled `state_at` latency;
- integrity verification for v4.1 runs.

With `--gate`, the command evaluates the canonical acceptance limits and exits
with code 2 when any gate fails. `--expected-ticks` can pin the golden run to
its expected population, e.g. 4,781 ticks.

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

## Golden-run finding — 2026-09-24

The real v4.0 reference run contains 4,781 committed ticks and approximately
1.3 GiB of telemetry evidence/checkpoints. A direct simulation of v4.1 layout
revision 2 over the first 250 ticks produced approximately 80.2 MB of
uncompressed evidence. The dominant failure was structural schema churn:
`runtime.signal_knowledge` alone generated about 29.8 MB of schema definitions
plus about 21.4 MB of structural frames in that window.

A keyed path-delta prototype reduced the same 250-tick window to approximately
24.9 MB, proving the direction is materially better, but this still projects
above the <200 MB hard gate for the full run. Therefore layout revision 2 is not
canonicalized and the default Physics3D writer remains v4.0.

Revision 3 proved the temporal semantics but remained too large in JSON.
Revision 4's binary representation passes the golden storage projection and is now the canonical writer for new runs. Remaining work is validation hardening and further optimization, not another storage-model redesign.

## Golden-run revision 4 result — 2026-09-24

A standalone implementation of the revision 4 physical encoding was run across
all 4,781 ticks of the real v4.0 reference run. During that pass every
reconstructed v4.0 state and Tick3D summary was checked against its committed
SHA-256 before being measured.

Estimated revision 4 evidence size: **125,965,909 bytes (125.97 MB)** excluding
large organism/physical checkpoints.

Breakdown:

- dense frames: 57.26 MB;
- structural deltas: 42.35 MB;
- events: 8.97 MB;
- global string dictionary: 7.80 MB;
- Tick3D summary frames: 5.55 MB;
- dense schemas: 2.97 MB;
- anchors: 0.39 MB;
- tick commits: 0.55 MB;
- exact fallback: 0.038 MB.

This passes the <200 MB hard storage gate and lands inside the 50–150 MB target. Revision 4 is therefore used as the default writer for new runs. Exact repository round-trip, latency and regression gates remain mandatory follow-up validation and may trigger fixes or rollback, but they no longer block using the achieved revision.

## Canonicalization gate

Revision 4 is the default writer. The gates below remain the acceptance checklist for hardening and future optimization; any reconstruction or integrity failure is still a release-blocking defect.

## Acceptance gates

Before treating v4.1 as scientifically validated on the reference 4,781-tick
run:

- 100% state reconstruction equality;
- 100% Tick3D reconstruction equality;
- evidence storage < 200 MB excluding checkpoints;
- target 50–150 MB;
- fallback < 5% of evidence bytes;
- state_at p95 < 100 ms;
- revision 4 uses a default 256-tick telemetry anchor interval to bound
  random-access replay while keeping large organism/physical checkpoints on
  their independent 1,024-tick cadence;
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
- float quantization or approximate numeric codecs;
- gzip/zstd/zip as the primary storage model.

Binary typed records and varints are part of revision 4 because the golden run
showed that JSON textual overhead remained the dominant blocker after temporal
redundancy was removed.
