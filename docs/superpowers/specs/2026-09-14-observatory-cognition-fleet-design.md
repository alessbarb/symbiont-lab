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

```
Symbiont A (resident)
      │
      ├─ instance registry file   (heartbeat, identity)
      ├─ journal (ndjson)         (per-tick CognitionState + organism snapshot)
      └─ checkpoint               (durable, unrelated to Observatory)
      │
      ▼
Observatory local server (127.0.0.1 only)
      │  watches registry + tails journals
      │  SSE (unidirectional, server → browser)
      ▼
Browser: Fleet view → per-instance dashboard (existing tabs + new Cognition tab)
```

Existing transports (`--stdout` envelopes, `write_replay` files,
`postMessage`/`BroadcastChannel`) are kept as-is, not replaced. The SSE
server is an additional consumer of the same publish path.

## Identity and discovery

Each resident process, at startup, generates:

- `run_id`: a fresh ULID/UUID for this process execution — unique every
  launch, even resuming the same `--state-file`.
- `instance_id`: stable identity for "this resident configuration"
  (derived from the resolved `--state-file` path, so resuming the same
  state file is recognized as the same instance across restarts).

Registry file: `~/.local/state/symbiont/observatory/instances/<instance_id>.json`,
atomically rewritten each heartbeat (same atomic-write pattern as
`write_replay`):

```json
{
  "instance_id": "inst_...",
  "run_id": "run_...",
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
with one `publish(snapshot, cognition_state)` call fanning out to sinks,
so every transport sees the identical projected data:

- `StdoutSink` — today's behavior, unchanged output.
- `JournalSink` — appends one ndjson line to
  `~/.local/state/symbiont/observatory/instances/<instance_id>.ndjson`,
  rotated/bounded the same way `write_replay` bounds `MAX_TICKS`
  (truncate oldest lines past the cap). This is a journal (transport
  aid for the SSE server to tail/replay-on-connect), not a second
  source of truth — the runtime checkpoint remains the only durable
  organism state.
- `ReplaySink` — wraps existing `write_replay`.

`resident.py` also writes/refreshes the registry heartbeat file each
tick (or on a fixed wall-clock cadence if ticks are slower than the
heartbeat TTL needs).

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
  quantized Huber loss, same quantization bins as
  `checkpoint.py`'s existing weight/eligibility quantization),
  `edge_deltas[]` (edge id → weight_class/eligibility_class, quantized,
  only for edges whose class changed since last published tick — not
  the full edge table every tick), `mutations[]` (this tick's
  structural mutations: `{kind, node_id|edge_id}`), `safety_state`
  (`consecutive_failures`, `frozen`).
- **`instance.schema.json`** — the registry record shape above.

`replay.schema.json` gains a sibling `topology_replay.schema.json`
reference is not needed — topology is small and infrequent enough to
just be fetched fresh on connect/revision-change, not replayed
tick-by-tick.

## Versioning strategy

`snapshot.schema.json`'s `schema_version` moves from `const 1` to
accepting `1` or `2` (`2` = same shape plus the optional `cognition`
field). The frontend gets a normalizer:

```
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
`~/.local/state` directly), two responsibilities:

1. Poll the registry directory, emit Fleet membership/liveness over one
   SSE stream.
2. Per selected instance, tail its journal ndjson file and forward new
   lines as SSE events on a per-instance stream; on connect, send the
   last N lines (bounded, e.g. 200) so a newly opened tab isn't empty,
   plus the current topology (read once, then only re-sent when
   `topology_revision` changes).

The server only reads files organisms write. It never writes into any
`--state-file`, checkpoint, or registry entry belonging to an organism.

## Testing

- `test_adapter.py` gains cases for `project_tick(..., cognition=None)`
  (unchanged v1 output) and `project_tick(..., cognition=<result>)`
  (v2 output, `cognition` field present, schema_version 2).
- New `test_registry.py`: heartbeat write/read, alive/stale/TTL-expiry
  classification, atomic-write pattern.
- New `test_journal.py`: append, bounded rotation, sink fan-out
  (`publish()` reaches all sinks with identical payload).
- New `test_server.py`: binds only to 127.0.0.1; SSE stream shape for
  Fleet membership and per-instance tail; replay-on-connect bound.
- Frontend: manual verification (start 2+ real residents with
  `--genome-file`/`--graph-file`, open Observatory, confirm Fleet shows
  both, confirm Cognition tab shows live readouts/topology for each).

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
