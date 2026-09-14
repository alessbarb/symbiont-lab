# Observatory: cognition-aware, multi-instance, real-time design

Status: approved by owner 2026-09-14. Supersedes nothing; extends
`observatory/README.md`'s existing note that "a localhost read-only
transport can be added later, inside the observatory, once the runtime
has stable state."

## Problem

Observatory today (`observatory/adapter.py`, `resident.py`,
`snapshot.schema.json` v1) can only display one hardcoded
`--state-file` instance, has no concept of discovering other resident
Symbionts on the machine, and carries zero awareness of the v0.55-59
cognition layer (genome, `CognitiveGraph`, learning, structure,
`SafetyState`). The owner wants real-time visibility into all
resident/existing symbionts on the machine, including full cognition
state, while Observatory stays passive per CLAUDE.md: "organism state
may flow outward for display; the display does not control cognition."

## Non-goals

- No cross-organism cognition, no collective/social behavior. Fleet is
  an inventory of independently observed processes, never a merged
  "population" of cognition. That leap is a separate, later milestone
  (Milestone F territory), not this one.
- No control channel back into any organism. Every new file this design
  introduces is organism-written, Observatory-read only.
- No new permission class, no network exchange, no identifying host
  data. All transport stays on `127.0.0.1` / local filesystem.

## Architecture

```text
Symbiont A (resident)
      │
      ├─ instance registry file   (heartbeat, identity)
      ├─ topology file            (rewritten only when topology_revision changes)
      ├─ journal (ndjson segments) (per-tick CognitionState + organism snapshot)
      └─ checkpoint               (durable, private organism state — Observatory never reads this)
      │
      ▼
Observatory local server (127.0.0.1 only)
      │  watches registry, reads topology, tails journal segments
      │  SSE (unidirectional, server → browser)
      │  never imports symbiont.core — understands only Observatory contracts
      ▼
Browser: Fleet view → per-instance dashboard (existing tabs + new Cognition tab)
```

Four artifacts per instance, each with one writer (the organism) and one
reader (Observatory):

```text
instances/
├── <instance_id>.json              registry: identity + heartbeat
├── <instance_id>.topology.json     structure: nodes/edges, revision-gated
└── <run_id>-NNNNNN.ndjson          journal segments: per-tick state
```

The checkpoint stays exactly what it is today — durable, private,
internal to the organism. Observatory never reads it; reading it would
collapse the separation between persistence and the observation
contract. Everything Observatory needs is republished into the three
files above.

Existing transports (`--stdout` envelopes, `write_replay` files,
`postMessage`/`BroadcastChannel`) are kept as-is, not replaced. The SSE
server is an additional consumer of the same publish path.

## Identity and discovery

Each resident process, at startup, generates two identifiers:

- `instance_id`: stable identity for "this resident configuration" —
  same across restarts of the same `--state-file`.
- `run_id`: unique per process execution — always new, even resuming
  the same `--state-file`.

`instance_id` is derived as `sha256(namespace || resolved_state_file_path)[:16]`
— a stable hash, never the raw path itself, so the registry contract
never exposes filesystem layout or usernames. `run_id` is a `uuid4`
(stdlib `uuid` module — no new dependency for ULID/UUID7) generated
fresh every process start, so restarting against the same `--state-file`
keeps `instance_id` stable but always gets a new `run_id`.

Registry file: `~/.local/state/symbiont/observatory/instances/<instance_id>.json`,
atomically rewritten each heartbeat (same atomic-write pattern as
`write_replay`):

```json
{
  "instance_id": "8f2c1a9b4e6d0731",
  "run_id": "01931c2e-...",
  "pid": 18342,
  "display_id": "local-symbiont",
  "started_at": "2026-09-14T12:00:00Z",
  "last_heartbeat": "2026-09-14T12:05:00Z",
  "topology_revision": 17
}
```

`pid` is an auxiliary hint only, never the liveness authority (PIDs are
reused). Liveness is judged purely from `last_heartbeat` age:

- `alive`: heartbeat within `2 * interval_seconds`
- `stale`: heartbeat older than that but within a TTL (default 10
  minutes)
- past TTL: the server stops listing the instance in Fleet at all — no
  indefinite "dead" graveyard. The registry file itself is left alone
  (Observatory never deletes organism-written files); a new resident
  launch or an explicit `observatory maintenance --prune` step may
  remove stale registry files. This preserves the one-way rule:
  organism writes, Observatory only reads (never mutates organism
  state space).

## Publishing (resident.py refactor)

Replace the current single `print(json.dumps(envelope(snapshot)))` call
with a `SnapshotPublisher` fanning out to sinks with different shapes,
so every transport sees the identical projected data without forcing a
single append-only interface onto things that aren't append-only:

- `StdoutSink.write(envelope)` — today's behavior, unchanged output.
- `JournalSink.write(envelope)` — appends one ndjson line, tagged with
  `run_id` and a monotonic `sequence` (not `tick`) as the transport
  identifier:

  ```json
  {"run_id": "01931c2e-...", "sequence": 9184, "snapshot": {}}
  ```

  `sequence` increments once per publish within a `run_id` regardless
  of `tick` semantics, so SSE reconnects can resume unambiguously
  ("give me everything after sequence 9180") without relying on file
  offsets. Journals are **segmented**, not truncate-in-place — truncating
  a file a tailer has an open file descriptor on shifts offsets under
  it and risks duplicated or dropped events for a live SSE reader.
  Segments: `~/.local/state/symbiont/observatory/instances/<run_id>-NNNNNN.ndjson`,
  each capped at a fixed line count; once full, the sink closes it and
  opens `NNNNNN+1`. A bounded number of the oldest segments for that
  `run_id` are deleted (never truncated) once the total exceeds the
  cap — deleting a whole closed segment is safe because no tailer has
  it open for appends by the time it is rotated out.
- `ReplayRecorder.record(snapshot)` — a distinct abstraction, not a
  sink pretending to be one: it accumulates snapshots and decides its
  own flush point, then calls the existing `write_replay()` unchanged.
  `write_replay()` was never append-oriented (it takes the full
  collection and writes the replay file atomically in one shot); this
  keeps that truth in the type instead of forcing it through
  `sink.write(envelope)`.

`resident.py` also writes/refreshes the registry heartbeat file each
tick (or on a fixed wall-clock cadence if ticks are slower than the
heartbeat TTL needs), and rewrites the topology file — atomically,
same pattern as the registry — only when `topology_revision` actually
changes (i.e. only on ticks with a structural mutation), never on
every tick.

## Schema split

Today's `snapshot.schema.json` stays the per-tick, display-bound,
`additionalProperties: false` contract it already is — no cognition
fields added directly into it. Three new schema files, same
conventions (bounded, closed, no raw host identifiers):

- **`topology.schema.json`** — `CognitionTopology`: `genome_id`,
  `kernel_version`, `topology_revision`, `nodes[]` (id, kind, bias, tau
  — static/exact, matches `PlasticNode`'s already-exact-persisted
  fields), `edges[]` (source_id, target_id, kind — structural only, no
  weight). Changes rarely — only on a structural mutation.
- **`cognition_state.schema.json`** — `CognitionState`, referenced from
  `snapshot.schema.json`'s `organism` object as one new optional field
  `cognition` (this is the one additive touch to the existing schema,
  gated by bumping `schema_version` — see versioning below):
  `topology_revision` (which topology this state applies to),
  `readouts{}` (id → value), `prediction_errors{}` (predictor_id →
  `loss_class`, quantized independently — see below), `edge_deltas[]`
  (edge id → weight_class/eligibility_class, quantized with
  `checkpoint.py`'s existing weight/eligibility bins since those are
  literally the same quantities, only for edges whose class changed
  since last published tick — not the full edge table every tick),
  `mutations[]` (this tick's structural mutations: `{kind,
  node_id|edge_id}`), `safety_state` (`consecutive_failures`, `frozen`).
- **`instance.schema.json`** — the registry record shape above.

`prediction_errors` gets its own quantization, not a reuse of the
weight/eligibility bins: a Huber loss has a different distribution and
meaning than a weight or an eligibility trace, so sharing the
*discipline* (bounded, discrete classes, never a raw float) is right
but sharing the *thresholds* is not. `loss_class` is one of `zero`,
`trace`, `low`, `medium`, `high`, `extreme`, with cut points defined
and unit-tested specifically against Huber-loss magnitudes (derived
during implementation from observed loss ranges in
`test_cognition_bridge.py`'s existing fixtures, not guessed).

A replay-of-topology schema is not needed — topology is small and
infrequent enough to just be read fresh from `<instance_id>.topology.json`
on connect and again whenever `topology_revision` changes, not
replayed tick-by-tick. The server reads this file directly (it is the
fourth per-instance artifact, alongside registry and journal — see
Architecture); it never derives topology from the checkpoint or from
importing `symbiont.core`.

## Versioning strategy

`snapshot.schema.json`'s `schema_version` moves from `const 1` to
`enum: [1, 2]`, with the presence of `cognition` tied to the version
by an explicit conditional rather than left merely optional — a
schema that just marks `cognition` optional would silently accept a
`schema_version: 1` payload carrying `cognition`, or a `2` payload
without it, both of which contradict the intended meaning:

```json
{
  "if": { "properties": { "schema_version": { "const": 1 } } },
  "then": { "properties": { "organism": { "not": { "required": ["cognition"] } } } },
  "else": { "properties": { "organism": { "required": ["cognition"] } } }
}
```

i.e. `schema_version: 1` MUST NOT carry `cognition`; `schema_version: 2`
MUST carry it. That makes "v1 stays exactly v1" a checked fact, not a
convention. The frontend gets a normalizer:

```text
v1 snapshot ─┐
             ├─→ normalize() → internal model → render
v2 snapshot ─┘
```

Old replay files (schema_version 1) keep working unmodified — the
normalizer treats a missing `cognition` field as "no cognition data for
this organism" (e.g. an organism with no genome/graph configured),
never as an error. `adapter.py`'s `project_tick` gains an optional
`cognition: CognitionBridgeResult | None` parameter; passing `None`
keeps today's exact v1 output (schema_version stays 1 in that case —
only bump to 2 when a `CognitiveBridge` is actually present).

## Fleet UI

New sidebar: instances from the registry (via SSE), each row =
`display_id`, `instance_id` (short form), alive/stale badge. Selecting
an instance switches the existing dashboard (Overview, Senses, Beliefs,
history tabs — unchanged) to that instance's live snapshot stream, and
adds a new **Cognition** tab:

- Topology summary (node/edge counts, genome_id, kernel_version)
- Live readouts (current values)
- Prediction-error trend (sparkline per predictor from recent ticks)
- Structural mutation log (`topology_revision N → N+1: ADD_EDGE(...)`,
  etc. — surfaced as a first-class event, not a graph diff)
- Safety state (frozen indicator, consecutive_failures)

No cross-instance merged view is built. A population-of-real-instances
concept, if ever wanted, is explicitly out of scope here (see
Non-goals).

## Server

New `observatory/server.py`: binds `127.0.0.1` only (refuse to bind
elsewhere), no auth (single local user, same trust boundary as reading
`~/.local/state` directly), three responsibilities:

1. Poll the registry directory, emit Fleet membership/liveness over one
   SSE stream.
2. Per selected instance, tail its journal segments (following
   `run_id`+`sequence`, not file offsets) and forward new lines as SSE
   events on a per-instance stream; on connect, send the last N lines
   (bounded, e.g. 200) so a newly opened tab isn't empty.
3. Per selected instance, read `<instance_id>.topology.json` once on
   connect and again only when the registry's `topology_revision`
   advances.

The server understands only Observatory's own contracts (registry,
topology, journal/snapshot schemas) — it never imports `symbiont.core`
or any cognition module to reconstruct state, and it only reads files
organisms write. It never writes into any `--state-file`, checkpoint,
or registry entry belonging to an organism.

## Testing

- `test_adapter.py` gains cases for `project_tick(..., cognition=None)`
  (unchanged v1 output, `schema_version` stays 1) and
  `project_tick(..., cognition=<result>)` (v2 output, `cognition`
  field present, `schema_version` 2).
- New `test_registry.py`: heartbeat write/read, `instance_id` derived
  as a path hash (never the raw path), `run_id` regenerated across
  restarts of the same `--state-file`, alive/stale/TTL-expiry
  classification, atomic-write pattern.
- New `test_topology.py`: topology file rewritten only when
  `topology_revision` changes, unchanged on ticks with no structural
  mutation, atomic-write pattern.
- New `test_journal.py`: segment rotation (new segment file once the
  line cap is hit, old segments deleted whole once the total cap is
  exceeded, never truncated in place), `run_id`+`sequence` ordering,
  `SnapshotPublisher` fan-out (`StdoutSink`/`JournalSink`/
  `ReplayRecorder` all see the identical projected snapshot).
- New `test_loss_class.py`: `loss_class` cut points against Huber-loss
  fixtures already used in `test_cognition_bridge.py`, independent of
  the weight/eligibility quantization bins.
- New `test_server.py`: binds only to 127.0.0.1; SSE stream shape for
  Fleet membership and per-instance tail; replay-on-connect bound;
  topology re-sent only on revision change.
- New `test_observatory_integration.py`: launches two temporary real
  residents (distinct `--state-file`s) against the server, asserts two
  distinct registry entries with two distinct `run_id`s, independent
  Fleet selection/SSE streams for each, and that restarting one
  resident against the same `--state-file` keeps its `instance_id` but
  produces a new `run_id`.
- Frontend: manual verification (start 2+ real residents with
  `--genome-file`/`--graph-file`, open Observatory, confirm Fleet shows
  both, confirm Cognition tab shows live readouts/topology for each) —
  in addition to, not instead of, the automated integration test above.

## Decisions locked (owner, 2026-09-14)

1. `instance_id`/`run_id` identity, not PID-trust.
2. SSE, unidirectional, localhost-only.
3. Registry + journal are passive infrastructure (organism writes,
   Observatory only reads; no physical pruning of live entries by the
   server).
4. `CognitionTopology` (rare-changing) separated from `CognitionState`
   (per-tick).
5. v1 snapshots keep working via a frontend normalizer while new
   producers emit v2.
6. Fleet observes independent instances; it does not create collective
   cognition. That is future, separate work.

## Gaps closed (owner review, 2026-09-14, second pass)

1. Topology gets its own artifact (`<instance_id>.topology.json`),
   never read from the checkpoint.
2. `schema_version`/`cognition` presence is a checked `if/then`
   condition, not merely an optional field.
3. `prediction_errors` gets its own `loss_class` quantization,
   independent of the weight/eligibility bins.
4. Journal uses real segment rotation (delete whole closed segments)
   instead of truncate-in-place; entries are addressed by
   `run_id`+`sequence`, not `tick` or file offset.
5. `ReplayRecorder` is a distinct abstraction from the per-envelope
   sinks, matching what `write_replay()` actually is.

Plus two hardening details: `instance_id` is a path hash, never a raw
path; `run_id` uses stdlib `uuid4`, no new dependency. And the server
constraint is explicit: it never imports `symbiont.core`.
