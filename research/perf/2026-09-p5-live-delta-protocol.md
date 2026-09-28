# P5 — Live Observation Anchors + Deltas

Status: implementation candidate  
Base: P4 decoupled execution rates on `main`

## Scope

Telemetry v4.1 already stores temporal state using typed delta streams and
anchors. P5 therefore does **not** create a second storage format.

P5 targets the live observer transport between Physics3D projections,
`ObservationBus`, SSE and the browser.

## Protocol

Contract:

```text
observer-live-delta-v1
```

Compressed channels:

- `body`
- `cognition`
- `vitals`
- `mind_snapshot`
- `observed_frame`

Excluded channels:

- `body_pose`: already a lightweight high-frequency presentation frame;
- `world_scene`: already owns a domain-specific revisioned snapshot/delta
  contract.

Each compressed channel has an independent monotonic revision.

An anchor contains:

```json
{
  "type": "observation_delta",
  "contract": "observer-live-delta-v1",
  "channel": "cognition",
  "kind": "anchor",
  "revision": 17,
  "state": { "...": "materialized event" },
  "state_sha256": "..."
}
```

A delta contains:

```json
{
  "type": "observation_delta",
  "contract": "observer-live-delta-v1",
  "channel": "cognition",
  "kind": "delta",
  "revision": 18,
  "base_revision": 17,
  "patch": [
    {"op": "set", "path": "/tick", "value": 42}
  ]
}
```

Changed arrays are replaced atomically. Stable object trees are patched by path.

## Recovery rules

A client applies a delta only when:

```text
base_revision == locally materialized revision
revision == base_revision + 1
```

Otherwise the channel is considered stale and no partial state is rendered.

Recovery occurs through one of three paths:

1. periodic channel anchor;
2. new subscription, which receives the latest materialized anchor per channel;
3. queue overflow, which replaces the current delta with a materialized anchor
   for that channel immediately.

If a reconnect asks for a `Last-Event-ID` that has already fallen out of the
retained history, the bus sends current anchors rather than an orphan delta
chain.

Initial anchors are ordered by transport sequence so browser resume state never
moves backwards.

## Integrity and cost

Anchors carry a SHA-256 commitment to their materialized state.

Deltas deliberately do not hash the complete resulting state. Doing so would
serialize the full payload on every update and recreate much of the JSON cost
P5 is intended to remove. Delta integrity is instead guarded by strict
revision continuity; durable scientific integrity remains the responsibility
of Telemetry v4.1.

The diff path performs structural comparison directly and does not JSON-encode
subtrees merely to compare them.

## Browser reconstruction

`stream-delta.js` is the presentation-side reference patcher.

Mind and Body decode the transport envelope before their existing event
dispatch, so their internal contracts remain `body`, `cognition`,
`vitals`, `mind_snapshot` and `observed_frame`.

A revision gap clears the local channel state and refuses further deltas until
an anchor is received. No mixed-revision UI state is permitted.

## Acceptance contract

P5 is accepted when:

1. anchor + delta replay reconstructs the exact original observer event;
2. field addition, mutation and removal are preserved;
3. revision gaps cannot produce a rendered hybrid state;
4. slow-consumer overflow recovers through an immediate anchor;
5. history overflow recovers through current anchors;
6. `body_pose` and `world_scene` retain their existing contracts;
7. a representative large stable cognition structure produces a delta
   materially smaller than the equivalent full JSON event;
8. the protocol remains observer-only and cannot feed state back to Symbiont.

P6 may now optimize SSE framing, buffering and redundant parsing without
changing the logical observation protocol.
