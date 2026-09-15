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
| P1 | Browser modules share a mutable singleton in `state/store.js` | Hidden ordering assumptions between ingest, selection and rendering | Add explicit state transition functions and a narrow render request queue |
| P2 | Python resident modules use script-local imports (`from adapter import ...`) | Running as a module/package is less predictable than running the documented script path | Add a package entry point or central launcher without changing the CLI contract |
| P2 | Schema validation is split between JSON schemas and defensive normalizers | A field can be accepted by one boundary and dropped by another without one visible report | Add a contract matrix mapping each snapshot version to accepted projections |
| P3 | Replay and live streams share ingestion indirectly through UI modules | Transport behavior is harder to test without a DOM | Keep ingestion pure and move UI notifications to the caller |
| P3 | `render/` contains both presentation and selection/inspector orchestration | Visual changes can accidentally alter navigation state | Separate pure view-model builders from DOM writers incrementally |

## Explicit non-goals

This inventory does not authorize network transport, peer discovery, host writes,
commands, remediation, process inspection or propagation. Any such capability would
require a separate design and consent review.

## Validation baseline

The current Observatory contract suite is `pytest -q observatory/tests` (163 tests
passing at the time this inventory was written). This suite validates contracts and
integration boundaries; it is not a substitute for visual QA across browsers.
