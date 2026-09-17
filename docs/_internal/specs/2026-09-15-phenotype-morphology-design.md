# Observatory PR2: deterministic phenotype morphology

Status: approved by owner 2026-09-15; revised 2026-09-15 after owner
code review against the real wire contracts (topology field names,
percept/topology-sense mismatch, replay format, render ordering — see
"Revision history" at the end). Implements Phase 2 of
`docs/design/digital-body-schema-and-emergent-morphology.md` (§13-17,
§22-23, §27, §31), the second PR of that doc's 6-PR sequence (§36).
Builds on PR1 (`observatory/{state,projection,transport,render,ui}/`
module split, already merged).

## Problem

`render/organism.js` draws every organism — demo, a real schema-v1
sensory-development organism, or a real schema-v2 genome/graph
organism — inside the same hand-authored `cellPath` SVG constant. Two
organisms with completely different identity, sense counts, or
cognitive structure render as the same shape. Separately, the full
cognitive topology (`payload.topology`: `genome_id`, `nodes`, `edges`)
that real organisms already publish over SSE is fetched and
immediately discarded after computing two numbers for a text summary —
none of the graph's actual structure ever reaches the visual.

## Non-goals

- No Phenotype/Self view toggle (PR3), no `BodySchema` (PR4+).
- No merging of `organism.beliefs` (narrative/evidence) with
  `topology.nodes` (structural graph). They are different data models
  with no shared key; PR2 keeps them visually and semantically separate
  (owner decision 2026-09-15).
- Decorative belief-edge lines stay **only in demo** (no topology ever
  exists there); they are suppressed once a real organism's topology
  drives real fibres, to avoid two visually indistinguishable line
  types — "real cognitive edge" and "arbitrary `belief[i+4]`" — coexisting
  in the same figure (owner correction 2026-09-15, point 9).
- No new backend/schema fields. Every morphology input must already be
  exported today by `adapter.py`/the snapshot or topology schemas.

## Data flow changes

### Topology normalization (new: `projection/topology.js`)

The server (`server.py:_stream_instance`) reads the topology JSON file
and only checks `isinstance(topology, dict)` before sending it over
SSE — the schema's bounds (max 128 nodes, max 1024 edges, known
`kind` enums, id length limits) are never re-checked client-side.
`projection/snapshot.js` already has this exact pattern for snapshots
(`boundedSnapshot`); topology needs its own equivalent, since PR2 is
about to iterate/position these arrays as geometry:

```js
function boundedTopology(raw) {
  // -> { genomeId, topologyRevision, nodes: [{id, kind}], edges: [{sourceId, targetId, kind}] }
  // or null if raw is missing/malformed.
  // - requires genome_id, kernel_version, topology_revision to be present and
  //   within the schema's length/range bounds (server only checks isinstance(dict) —
  //   this is the real defensive boundary)
  // - caps nodes to 128, edges to 1024
  // - keeps only nodes whose kind is one of sense/concept/state/predictor/gate/readout
  // - drops any node whose node_id duplicates an already-kept node_id
  // - keeps only edges whose kind is one of excitatory/inhibitory/predictive/gating
  //   AND whose source_id/target_id are non-empty strings (existence of those ids
  //   against the node set is resolved later, inside morphology.js's unified
  //   receptor+internal anchor registry — not here, and not in render/organism.js)
  // - renames node_id -> id, source_id/target_id -> sourceId/targetId
}
export { boundedTopology };
```

This is also where the wire's real field names (`node_id`, `kind`,
`bias`, `tau` on nodes; `source_id`, `target_id`, `kind` on edges — not
`node.id`/`edge.source`/`edge.target`) get normalized away, so
`morphology.js` and `render/organism.js` never see raw wire shapes.

### State additions and resets

1. `transport/instance-stream.js`:
   - On `payload.topology`: `state.topology = boundedTopology(payload.topology);` in addition to the existing `renderCognitionTopology(payload.topology)` call, then re-render the organism view (`if (state.view === "individual") renderOrganism();`) — topology arrives independently of the per-tick snapshot stream (server only resends it when `topology_revision` changes).
   - On `connectInstance(instanceId)` switching to a different instance: set `state.instanceId = instanceId;` and immediately `state.topology = null;` (and `state.cognition = null;` for the same reason, even though it self-heals on the next tick) **before** opening the new `EventSource`. Without the null resets, switching instances can render instance B's beliefs/senses inside instance A's leftover structural topology for the ~1s until B's first topology message arrives. `state.instanceId` starts `null`.
2. `transport/replay.js`: `loadReplayFile()` must set `state.topology = null;` before the first `ingestSnapshot(state.replay[0], false)` call. The replay format (`replay.schema.json` → `snapshot.schema.json`) carries only snapshots, never topology — a lingering `state.topology` from a prior live connection would otherwise render a replayed organism with another organism's structural graph. (`state.cognition` is not nulled here: a v2-schema replay snapshot can legitimately carry its own `organism.cognition` per tick, and `ingestSnapshot` sets it correctly on the very next line.)
3. `projection/snapshot.js`: `ingestSnapshot` must assign `state.cognition = projection.cognition;` **before** calling `renderOrganism()`, not alongside the existing `renderCognitionState(projection.cognition)` call — today's call order is `renderSenses(); renderOrganism(); ...; renderCognitionState(projection.cognition);`, so an assignment placed next to the `renderCognitionState` call would make `renderOrganism()` read the *previous* tick's `state.cognition`. Corrected sequence:

   ```js
   state.cognition = projection.cognition;
   // ...rest of existing state assignments...
   renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();
   renderCognitionState(projection.cognition);
   ```

4. `boundedCognition()` (`projection/snapshot.js`) currently drops `topology_health` and `recovering`, both present on the wire (`cognition_state.schema.json`). Add them to its return shape: `topologyHealth: string` (one of the six enum values, default `"germinal"` if absent/unknown — mirrors the Python-side default in `adapter.py::_cognition_state`), `recovering: boolean`.

`state.topology` and `state.cognition` both start `null`.

### Revision consistency gate

Cognition (`state.cognition.topologyRevision`) and topology
(`state.topology.topologyRevision`) arrive over independent channels;
the server generally sends topology before the journal entries for a
new revision, but a topology file read failure can leave nothing sent
for that instant. `render/organism.js`, when building morphology
input, must therefore compare the two and treat a mismatch as
"structure not yet available" rather than rendering stale structure as
current:

```js
const topologyIsCurrent = state.topology && state.cognition
  && state.topology.topologyRevision === state.cognition.topologyRevision;
const structuralSenses = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind === "sense") : [];
const internalNodes = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind !== "sense") : [];
const edges = topologyIsCurrent ? state.topology.edges : [];
```

This check lives in `render/organism.js` (it decides what to *pass*
into morphology), not inside `morphology.js` itself, which stays a
pure function of whatever it's given.

## `projection/morphology.js`

New file, zero imports, fully pure (per §22/§23 — no DOM, no `state.js`
coupling, no `Math.random`, no `topologyRevision`-driven repositioning —
see "Position stability" below). Single export:

```js
function projectPhenotypeMorphology({
  identitySeed,       // string
  percepts,           // [{id, quality, active}] — dynamic, from state.senses, unbounded here (already capped at 32 upstream)
  structuralSenses,   // [{id, kind: "sense"}] — topology SENSE nodes (post revision-gate), unrelated cap (topology allows up to 128 total nodes)
  internalNodes,      // [{id, kind}] — topology concept/state/predictor/gate/readout nodes
  edges,              // [{sourceId, targetId, kind}] — normalized topology edges
  topologyHealth,     // string | null — one of germinal/developing/connected/adaptive/degenerate/recovering, or null if no cognition yet
  recovering,         // boolean
  frozen,             // boolean
}) {
  return { boundaryPath, externalInputAnchors, receptorAnchors, internalAnchors, fibres, presentation };
}
export { projectPhenotypeMorphology };
```

### `identitySeed` definition

`render/organism.js` builds `identitySeed` from whichever identity is
actually observable, never from `displayId` alone — `display_id` is a
user-facing label (`registry.py`/`instance.schema.json` keep it
explicitly separate from `instance_id`, and it can repeat or change):

```text
live, topology present:  `${state.topology.genomeId}:${state.instanceId}`
live/replay, no topology: `replay:${state.displayId}`  (covers replay and any
                           schema-v1 organism with no genome/graph)
demo:                     "demo"
```

`instance_id` is the best *observational* identity available in PR2 —
not the organism's eventual ontological identity. When a future
milestone introduces a durable `organism_id` (continuity across
restarts/instances), that field should replace `instanceId` here
without `morphology.js` itself changing at all (it only ever sees the
resulting string).

### Canonical ordering (determinism, not just geometry)

Positions are seed+id stable, but the *arrays* `render/organism.js`
passes in are not otherwise guaranteed to arrive in a stable order
(topology JSON key order, SSE timing). `morphology.js` sorts its own
inputs before doing anything else — `structuralSenses`/`internalNodes`
by `id` (code-point comparison, i.e. plain `<`, never `localeCompare`),
`edges` by `(sourceId, targetId, kind)` — and preserves that order in
`receptorAnchors`/`internalAnchors`/`fibres`. This makes the "same
nodes/edges in a different array order → identical output" test an
actual determinism guarantee, not just a happy accident of stable
per-node hashing.

### Why `percepts` and `structuralSenses` are two separate inputs

`state.senses` comes from `organism.percepts`, capped at 32 dynamic
readings (quality/availability, refreshed every tick). Topology SENSE
nodes are structural and share the graph's 128-node budget — the
design doc's own worker-3 validation fixture (§33) has **58** SENSE
nodes, already exceeding the percept cap, so percepts cannot stand in
for structural sense count. When topology is current (per the
revision gate above): **`structuralSenses` defines the receptor set**
(periphery layout, one receptor per structural sense node); `percepts`
only *decorate* a receptor whose `id` matches a percept's `id`
(active/quality visuals) — a percept with no matching structural node
is not drawn as an extra receptor (no fabricated organ). When there is
no current topology (demo, schema v1): fall back to today's behavior —
`percepts` alone define the receptor set, exactly as `render/organism.js`
does today (`state.senses.forEach(...)`).

### Anchor registry (why SENSE-incident edges must not be dropped)

A single lookup covers every node topology can name, so an edge whose
endpoint is a `sense` node is not silently discarded (the original
draft's bug):

```text
topology node
     │
     ├── kind === "sense" → receptorAnchor  (id keyed)
     └── otherwise        → internalAnchor  (id keyed)

topology edge (sourceId, targetId)
     │
     └── lookup both ids in the combined receptor+internal anchor map
           found  → fibre {sourceId, targetId, kind, x1,y1,x2,y2}
           missing → dropped (id genuinely absent from this topology — not "wrong node kind")
```

`internalAnchors` carries every non-sense node, `kind` included
verbatim (`concept`/`state`/`predictor`/`gate`/`readout` — renamed from
the spec's earlier `conceptNodes`, which wrongly implied only
`concept`-kind nodes). There is no separate `coreAnchor` field: a
`readout`-kind node is just an `internalAnchor` with `kind: "readout"`;
`render/organism.js` styles anchors of that kind as the integrative
core. With zero readouts, nothing special renders. With several, each
renders as its own real structural node — no invented centroid.
`fibres` keep `kind` (`excitatory`/`inhibitory`/`predictive`/`gating`)
instead of reducing an edge to bare coordinates, so presentation can
style edge kinds differently later without re-deriving them.

### Position stability

A tiny self-contained FNV-1a string hash (using `Math.imul` for
correct 32-bit wraparound) seeds a mulberry32 PRNG. `identitySeed`
hashed once produces the boundary's control points (angularly ordered,
coordinates quantized via `toFixed` before the path string is built,
so output is byte-identical for a given seed on any platform/run) — a
closed cubic-spline path, generated instead of the hardcoded `cellPath`
(§14, §22's "same seed = same boundary" test). Each `internalAnchor`'s
position is seeded independently by `identitySeed + node.id` (not by
array index or `topologyRevision`), placed within a guaranteed-interior
region of the generated boundary (not merely its bounding box, which
could place a node outside an indented silhouette). **A node's position
is stable for as long as it exists**, full stop — `topologyRevision` is
*not* a morphology input at all (removing the earlier draft's
contradictory idea that positions were both seed-stable and
revision-modulated). A structural mutation changes the rendered
morphology only because nodes/edges genuinely appear or disappear
between revisions; animated transitions between revisions are future
work, not PR2.

### Presentation, not a fabricated "confidence"

The original draft computed `confidence` as the mean of
`state.senses[].quality` and used it to brighten/dim the whole
organism. `quality` is *sensory/percept* quality (nominal/degraded/
stale/unavailable, per organism, per reading) — not organism-level
self-confidence, and using it that way overloads a receptor-local
signal into a body-wide one that doesn't mean what it looks like it
means. Cognition already exports two real, bounded, organism-level
signals that *do* mean this: `topology_health` and `recovering`
(point 7). PR2 drops the invented `confidence`/`health` entirely and
derives `presentation` from real data instead:

```js
presentation: {
  boundaryTension: (recovering || topologyHealth === "recovering" || topologyHealth === "degenerate") ? 0.7 : 1,
  desaturated: frozen === true,
  reducedMotion: frozen === true,
}
```

(`recovering` is its own boolean on the wire, distinct from the
`topology_health: "recovering"` enum value — both feed the same visual
signal here since either one means "the organism itself reports it's
recovering," but neither is dropped from the input contract just
because one example use folds them together.)

(`quality` still drives each receptor's own active/dim styling, same
as today — just scoped to the receptor it belongs to, never the whole
boundary.) Exact multiplier values are implementation detail for the
plan, not the spec; the principle — only real per-tick cognition
signals modulate presentation, position/structure never do — is what's
being fixed here.

## `render/organism.js` changes

Replace the hardcoded `cellPath` constant and the fixed-formula sense
placement with a call to `projectPhenotypeMorphology(...)` built from
`state` per the revision gate above, then draw:

- `boundaryPath` where `cellPath` was drawn (two `<path>`s: fill +
  outline, same as today) — CSS classes renamed `.membrane` →
  `.phenotype-boundary`, `.membrane-inner` → `.phenotype-boundary-inner`
  (§27; `observatory/styles.css` selectors renamed to match; local
  `cellPath` var renamed `boundaryPath`; `#cell-fill` gradient id kept
  as-is since it's a fill technique, not a domain concept per §27's own
  carve-out).
- `externalInputAnchors` / `receptorAnchors`: today's single fixed-x
  sense position (`x: 75`) splits into two anchors per sense — a fixed
  legible `externalInputAnchor` (kept at `x: 75`, same as today) and a
  `receptorAnchor` computed on the real generated boundary (no longer
  the old fixed `x: 235`-ish guess, which had no relationship to a
  procedurally generated silhouette). The existing sensor-path curve
  between them, and the perception-pulse circle, are unchanged in
  behavior — only their anchor coordinates now come from the morphology
  result.
- `internalAnchors`/`fibres`: drawn (only ever non-empty for a real
  schema-v2 organism with *current* topology, per the revision gate) as
  additional `<circle>` regions — styled distinctly for `kind: "readout"`
  — and `<line>` fibres inside the boundary, before the existing belief
  circles/lines/attention-ring/dissent-path code.
- Belief circles/attention-ring/dissent-path: unchanged in every mode.
  Belief-edge decorative lines (the `belief[(index+4) % length]`
  neighbor lines): drawn only when `state.source === "demo"` — **not**
  `internalAnchors.length === 0`, which would wrongly let the fake lines
  reappear for a real schema-v1 organism (no genome/graph at all) or a
  real organism whose topology happens to contain only SENSE nodes
  (zero `internalAnchors` but still real, current topology). Any real
  organism, with or without topology, never draws invented belief
  relationships — only demo, which has no topology to be honest about
  in the first place, keeps them. Belief circles themselves, their
  click→`renderInspector()` behavior, attention-ring and dissent-path
  stay drawn in every mode, unaffected.

No changes to `render/inspector.js`, `render/senses.js`,
`render/population.js`.

## Testing

`observatory/test_morphology.py` (new): shells out to `node` (checked
via `shutil.which("node")`; the whole test class is `unittest.skipUnless`
when absent, so CI without Node doesn't hard-fail) to import and call
`projectPhenotypeMorphology` with fixture inputs, asserting on the
returned JSON:

- same input → byte-identical `boundaryPath` across two separate `node`
  invocations.
- two different `identitySeed`s → different `boundaryPath`.
- `topologyHealth`/`recovering`/`frozen` differing, same
  `identitySeed`/structure → same `boundaryPath` and same
  `internalAnchors` positions (presentation may only modulate rendering
  hints, never reseed geometry).
- `edges: []` → `fibres: []`, regardless of `internalNodes`/
  `structuralSenses` content.
- `structuralSenses: [], internalNodes: [], edges: []` (the demo/schema-v1
  shape) → `receptorAnchors` still derived from `percepts`,
  `internalAnchors: [], fibres: []`.
- a **SENSE → CONCEPT → READOUT** chain fixture (using real field names
  post-normalization: `id`/`kind` on nodes, `sourceId`/`targetId`/`kind`
  on edges) → both edges appear in `fibres`, including the one incident
  on the sense node — regression test for the "edges into SENSE get
  dropped" bug this revision fixes.
- an edge naming an id not present in either `structuralSenses` or
  `internalNodes` → silently dropped, not present in `fibres`.
- same nodes/edges in a different array order → identical output
  (order independence: canonical sort by `id`/`(sourceId,targetId,kind)`
  inside `morphology.js` itself, not an accident of per-node hashing).
- every `internalAnchor` position falls within the generated boundary's
  interior (not just its bounding box).

`observatory/test_topology.py` (new, small): `boundedTopology()` unit
tests in Python-callable-JS or plain-text-contract style consistent
with the rest of the suite — caps, unknown-kind filtering, and the
`node_id`→`id`/`source_id`→`sourceId`/`target_id`→`targetId` rename
specifically (regression test for the field-name bug this revision
fixes).

`observatory/test_contract.py`: update/add literal-text assertions —
`cellPath` constant must no longer exist anywhere in the frontend
bundle; `phenotypeBoundary`/`projectPhenotypeMorphology`/
`boundedTopology` should be present; existing sense/organism assertions
otherwise unaffected since `render/organism.js` still exports
`renderOrganism` the same way.

Additional Python-side integration coverage (extends
`observatory/test_server.py`/`test_observatory_integration.py` patterns,
exercised without Node): instance switch clears stale topology (assert
`state.topology`-equivalent behavior via a scripted two-instance SSE
sequence, or document as a manual Playwright check if not cheaply
scriptable in the existing harness); loading a replay after a live
connection clears topology; a `topology_revision` mismatch between
`state.cognition` and `state.topology` renders no structural
regions/fibres for that tick.

## Verification

- `pytest observatory/ -x` green (including the new,
  Node-conditional `test_morphology.py` and `test_topology.py`).
- Manual Playwright pass (same pattern as PR1): serve `observatory/`,
  confirm zero new console errors, confirm demo mode still shows
  boundary + 5 sense receptors + all 25 decorative belief
  circles/lines exactly as before (just inside a generated, not
  hardcoded, boundary; belief-edge lines still present since demo never
  has real topology), confirm no internal topology regions/fibres
  render in demo. A **live schema-v2 resident or a direct topology SSE
  fixture** (not a recorded replay — replay never carries topology, so
  it cannot exercise this path) additionally shows internal
  regions/fibres from its actual graph, a differently-shaped boundary
  than demo's, and belief-edge lines suppressed once real fibres are
  present.
- Exit condition (§31 Phase 2): two organisms with different
  phenotype/identity visibly differ, without invented structure.
- **Explicit acceptance fixture (worker-3, §33):** 58 SENSE, 5 CONCEPT,
  1 READOUT, 0 edges must render as 58 `receptorAnchors`, 6
  `internalAnchors` (5 concept + 1 readout), and `fibres: []` — with no
  belief-edge decoration (real organism, not demo) and no invented
  connectivity filling the visual gap left by zero edges. This is the
  concrete, checkable form of "morphology represents organization, it
  does not illustrate emptiness."

## Revision history

- 2026-09-15 initial version approved by owner.
- 2026-09-15 revised after owner code review against real code/schemas.
  Verified and incorporated: wire field names (`node_id`/`source_id`/
  `target_id`, not `id`/`source`/`target`) via new `projection/topology.js`;
  SENSE-incident edges were being dropped by the anchor lookup, fixed
  via a unified receptor+internal anchor registry; percepts (32-cap,
  dynamic) and topology SENSE nodes (128-node budget, structural) are
  distinct surfaces — structural senses now define the receptor set
  when topology is current, percepts only decorate; stale topology on
  instance switch / after loading a replay is now explicitly reset;
  added a `topologyRevision` consistency gate between cognition and
  topology; fixed `state.cognition` assignment ordering relative to
  `renderOrganism()`; dropped the invented sense-quality-average
  "confidence" input in favor of real `topology_health`/`recovering`
  cognition fields; sense anchors split into a fixed external-input
  point and a boundary-hugging receptor point; belief-edge decorative
  lines now suppressed once real fibres are present; renamed
  `conceptNodes`→`internalNodes`, dropped the separate `coreAnchor`
  field in favor of `kind: "readout"` anchors, kept edge `kind` in
  `fibres`; removed `topologyRevision` as a position-seeding input
  (positions are seed+id stable only); hardened the boundary generator
  (`Math.imul`, coordinate quantization, angular point ordering,
  guaranteed-interior anchor placement); corrected the Verification
  section's "recorded replay" claim (replay never carries topology).
- 2026-09-15 second review pass (no P0s remaining), four closures:
  canonical array ordering specified inside `morphology.js` itself
  (code-point `id` sort, `(sourceId,targetId,kind)` edge sort) so the
  determinism promise is real, not incidental; belief-edge suppression
  rule corrected from `internalAnchors.length === 0` (wrongly re-enables
  fake edges for a real schema-v1 organism or a real SENSE-only
  topology) to `state.source === "demo"`; `identitySeed` given a
  normative definition using the registry's `instance_id` (new
  `state.instanceId`, set in `connectInstance`) rather than the
  user-facing, non-unique `displayId`, with an explicit forward-compat
  note for a future `organism_id`; `boundedTopology`'s existence-check
  comment corrected to say the lookup happens inside `morphology.js`'s
  own unified anchor registry, and its required-field/duplicate-`node_id`
  validation made explicit; `presentation`'s example now uses the
  `recovering` boolean it previously took as input but never read.
  Added the worker-3 fixture as an explicit, numeric acceptance
  criterion in Verification.
