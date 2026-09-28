# P3 — Age-Independent World Journal

Status: implementation candidate  
Base: P2 sensorimotor matching on `main`

## Goal

The cost of World tick `t + 1` must not grow merely because the append-only
event history has grown to age `T`.

The full event journal remains available for replay, persistence recovery and
scientific audit. Live execution and passive bounded views must not require
replaying it.

## Journal indexes

`EventJournal` now maintains, incrementally on append:

- the first append index for each event id;
- committed events grouped by tick;
- an append-order prefix digest for every committed prefix.

It exposes bounded operations:

- `events_for_tick(tick)`;
- `tail(limit)`;
- `page_after(after, limit=...)`;
- `snapshot_range(start, stop)`;
- `prefix_digest(count)`.

`replay()` is intentionally preserved unchanged as the explicit full-history
operation.

Duplicate event ids preserve legacy cursor behavior: `page_after(id)` resolves
the first appended occurrence, exactly like the old linear scan.

## Live World

The live runtime no longer uses full replay for:

- acquisition metrics for the current tick;
- incremental event pagination;
- recent event payloads;
- ASCII event feed;
- recent per-organism damage projection.

Timeline arrays are now fixed-size deques rather than lists requiring
`pop(0)`.

Therefore, with current-world complexity held fixed, these operations are
independent of accumulated journal age.

## Persistence

The previous checkpoint path serialized the entire in-memory journal and then
re-read the complete durable prefix to prove continuity. Because checkpoints
run periodically from the World loop, that reintroduced age-dependent work.

P3 changes normal checkpoint persistence to:

1. capture universe state without embedding the journal;
2. verify the previously durable prefix using its incrementally maintained
   digest and tail event id;
3. serialize only `snapshot_range(previous_event_count)`;
4. append one new durable event segment;
5. store the new prefix digest in the manifest.

For manifests created before P3, one compatibility verification may reconstruct
the durable prefix once. Subsequent checkpoints use the digest path.

Checkpoint files still contain exact journal count and last event id, while
recovery reconstructs the required journal prefix from durable event segments
exactly as before.

## Verification

Tests explicitly forbid:

- `journal.replay()` in the live World metrics/projection path;
- `journal.snapshot()` during normal checkpoint persistence.

Additional tests verify indexed access equivalence, duplicate-id cursor
semantics, prefix-digest stability across snapshot/restore, and continued
detection of an incompatible in-memory journal prefix.

`scripts/bench_world_journal_index.py` measures indexed current-tick, tail and
cursor operations at increasing journal ages alongside the old replay-scan
reference.
