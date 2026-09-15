# Observatory architecture inventory

This is an inventory of the current implementation, not a proposal to expand the
Observatory's authority. The Observatory remains a passive, read-only apparatus.

## Boundaries that are currently working

- `projection/` validates and bounds external snapshots before they reach browser state.
- `transport/` reads replay, instance and Fleet streams; it emits no organism command.
- `state/` owns browser-local state and selectors.
- `render/` owns DOM/SVG presentation and accessible inspectors.
- `schemas/` closes the JSON wire contracts.
- `adapter.py` is a finite runtime-to-replay projection; `resident.py` publishes
  bounded artifacts; `server.py` is loopback-only static/SSE serving.
- The organism checkpoint is not read by the browser server or Fleet transport.

## Current dependency shape

```text
transport ──> projection ──> state
    │              │          │
    └──────────────┴──────> render ──> ui

resident/adapter ──> bounded JSON artifacts ──> server ──> browser transport
```

The browser entry point currently lets `projection/snapshot.js` trigger rendering
and lets render modules call back into state and projections. This is stable in the
current bundle, but it is intentionally recorded as coupling rather than presented
as a strict layering guarantee.

## Debt register

| Priority | Item | Consequence | Smallest safe follow-up |
| --- | --- | --- | --- |
| P1 | `projection/snapshot.js` still owns the render-cycle call (the renderer bridge is now isolated in `ui/render-cycle.js`) | Projection remains coupled to browser orchestration | Move the final render request to the application shell; keep ingestion pure first |
| P3 | Browser modules retain a mutable singleton in `state/store.js` | A few replay/UI fields still use shared state directly | Route remaining metadata changes through `state/transition.js` incrementally; keep snapshot commits atomic through `commitSnapshotProjection()` |
| P3 | The resident CLI still has two supported launch paths (module and script) | A future packaging change could let the paths drift | Keep both paths covered by the same contract/help smoke check |
| P3 | Schema validation is split between JSON schemas and defensive normalizers | A field can be accepted by one boundary and dropped by another without one visible report | Keep [`schemas/CONTRACT_MATRIX.md`](schemas/CONTRACT_MATRIX.md) and compatibility tests synchronized with schema changes |
| P3 | Replay and live streams share ingestion indirectly through UI modules | Transport behavior is harder to test without a DOM | Keep ingestion pure and move UI notifications to the caller |
| P3 | Resident restarts create a new journal run id | Raw NDJSON grows across runs | Segment rotation automatically refreshes a derived summary; explicit `Journal.compact()` gzips closed segments losslessly; no automatic deletion is permitted |
| P3 | Long histories are expensive to scan repeatedly | Operators need a compact view without losing auditability | `history_summary.py` emits derived counters, coverage and segment hashes on rotation while retaining raw records |
| P3 | `render/` contains both presentation and selection/inspector orchestration | Visual changes can accidentally alter navigation state | Separate pure view-model builders from DOM writers incrementally |

## Explicit non-goals

This inventory does not authorize network transport, peer discovery, host writes,
commands, remediation, process inspection or propagation. Any such capability would
require a separate design and consent review.

## Validation baseline

The current Observatory contract suite is `pytest -q observatory/tests` (163 tests
passing at the time this inventory was written). This suite validates contracts and
integration boundaries; it is not a substitute for visual QA across browsers.
