# Observatory PR2: deterministic phenotype morphology

Status: approved by owner 2026-09-15. Implements Phase 2 of
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
cognitive topology (`payload.topology`: genome_id, nodes, edges) that
real organisms already publish over SSE is fetched and immediately
discarded after computing two numbers for a text summary — none of the
graph's actual structure ever reaches the visual.

## Non-goals

- No Phenotype/Self view toggle (PR3), no `BodySchema` (PR4+).
- No merging of `organism.beliefs` (narrative/evidence) with
  `topology.nodes` (structural graph). They are different data models
  with no shared key; PR2 keeps them visually and semantically separate
  (owner decision 2026-09-15).
- No touching the existing decorative belief-edge lines
  (`belief.forEach` neighbor lines in `render/organism.js`) — pre-existing,
  unrelated to cognitive topology, out of scope.
- No new backend/schema fields. Every morphology input must already be
  exported today by `adapter.py`/the snapshot or topology schemas.

## Data flow changes

Two small additive state fields, both populated where the data already
arrives, neither changing any existing field:

1. `transport/instance-stream.js`: on `payload.topology`, in addition to
   the existing `renderCognitionTopology(payload.topology)` call, set
   `state.topology = payload.topology` and re-render the organism view
   (`if (state.view === "individual") renderOrganism();`). Topology
   arrives independently of the per-tick snapshot stream (server only
   resends it when `topology_revision` changes), so the organism view
   must be able to react to it on its own.
2. `projection/snapshot.js`: `ingestSnapshot` already computes
   `projection.cognition` and passes it straight to
   `renderCognitionState()` without persisting it. Add
   `state.cognition = projection.cognition;` alongside the existing
   `renderCognitionState(projection.cognition);` call, so morphology can
   read `frozen` state at any render time, not just at ingest.

`state.topology` starts `null` (demo, and any real organism before its
first topology message). `state.cognition` starts `null` similarly.
Both are plain data, never touched by anything outside
`transport/instance-stream.js` and `projection/snapshot.js`
respectively.

## `projection/morphology.js`

New file, zero imports, fully pure (per §22/§23 — no DOM, no `state.js`
coupling, no `Math.random`). Single export:

```js
function projectPhenotypeMorphology(input) {
  // input: { identitySeed, senseIds, conceptNodes, readoutNodes, edges,
  //          topologyRevision, health, confidence, frozen }
  return { boundaryPath, senseAnchors, internalAnchors, coreAnchor, fibres };
}
export { projectPhenotypeMorphology };
```

**Input** (built by `render/organism.js` from `state`, never passed
`state` itself):

- `identitySeed: string` — `` `${state.topology.genome_id}:${state.displayId}` `` when `state.topology` exists, else `state.displayId ?? "demo"`.
- `senseIds: string[]` — `state.senses.map(s => s.id)`.
- `conceptNodes: {id, kind}[]` — `state.topology?.nodes.filter(n => n.kind !== "sense" && n.kind !== "readout") ?? []`. Empty whenever there's no topology (demo, schema v1) — no fabricated internal structure (I5).
- `readoutNodes: {id}[]` — `state.topology?.nodes.filter(n => n.kind === "readout") ?? []`.
- `edges: {source, target}[]` — `state.topology?.edges ?? []`. Empty when no topology, so `fibres` is always `[]` too (I5, and answers the "demo shows 0 fibres" decision).
- `topologyRevision: number` — `state.topology?.topology_revision ?? 0`. Used only to admit *bounded* internal-layout change across revisions (§14: developmental state produces small changes around the stable baseline) — never to reseed the boundary itself.
- `health: number | null` — always `null` for PR2. No backend field represents organism "health" yet (that's Milestone F physiology, §7/§31 Phase 7); passing `null` keeps the boundary at neutral integrity rather than fabricating a number. The geometry function already treats it as optional per §13's own `number | null` type.
- `confidence: number | null` — mean of `state.senses.map(s => s.quality)` when `state.senses.length`, else `null`. A real, already-exported bounded value, not invented.
- `frozen: boolean` — `state.cognition?.safetyState?.frozen ?? false`.

**Determinism.** A tiny self-contained FNV-1a string hash seeds a
mulberry32 PRNG (both ~5 lines, no dependency). `identitySeed` hashed
once produces N (8–12, count derived from the hash so it's still a pure
function of the seed) control points around a base circle, each with a
small pseudo-random radius/angle jitter from the seeded PRNG stream —
rendered as a closed cubic-spline path exactly like the current
hand-authored `cellPath`, just generated instead of hardcoded. Same
`identitySeed` → byte-identical `boundaryPath`, always (§14, §22's
"same seed = same boundary" test). `confidence`/`health`/`frozen` may
apply a small *bounded* uniform scale/opacity modulation on top of the
already-generated boundary — they never reseed or regenerate its control
points, so playback ticking `confidence` doesn't jitter the organism's
basic identity shape.

**Layout.** `senseAnchors`: same deterministic evenly-spaced vertical
placement `render/organism.js` already computes today (fixed x, y
interpolated by index/count) — already deterministic, already scales
with `senseIds.length`, no reason to replace it. `internalAnchors`: for
each `conceptNodes`/`readoutNodes` entry, a position from the same
seeded PRNG stream (seeded by `identitySeed + node.id`, so each node's
position is independently stable regardless of array order), scattered
within the boundary's interior bounds. `coreAnchor`: centroid of
`readoutNodes` anchors, or `null` when there are none. `fibres`: for
each edge whose `source`/`target` both resolve to a known
`internalAnchor` (unresolvable edges — pointing at a `sense`/unknown
node kind — are simply skipped, not drawn as broken lines), a
`{sourceId, targetId, x1, y1, x2, y2}` entry.

## `render/organism.js` changes

Replace the hardcoded `cellPath` constant and the fixed-formula sense-y
placement with a call to `projectPhenotypeMorphology(...)` built from
`state` as above, then draw:

- `boundaryPath` where `cellPath` was drawn (two `<path>`s: fill +
  outline, same as today) — CSS classes renamed `.membrane` →
  `.phenotype-boundary`, `.membrane-inner` → `.phenotype-boundary-inner`
  (§27; `observatory/styles.css` selectors renamed to match, local
  `cellPath` var renamed `boundaryPath`, `#cell-fill` gradient id kept
  as-is since it's a fill technique, not a domain concept per §27's own
  carve-out).
- `senseAnchors` in place of today's inline per-sense `sensePositions`
  map/path-to-membrane computation (the sensor-path curves from each
  receptor to the boundary, and the perception-pulse circles, are
  unchanged in behavior — only their anchor coordinates now come from
  the morphology result instead of being computed inline).
- `internalAnchors`/`fibres` newly drawn (only ever non-empty for a
  real schema-v2 organism with topology loaded) as additional `<circle>`
  regions and `<line>` fibres inside the boundary, before the existing
  belief circles/lines/attention-ring/dissent-path code, which is
  otherwise **untouched** — same positions, same neighbor-line
  decoration, same click→`renderInspector()` behavior, for every data
  source including demo.
- `coreAnchor`, when non-null, drawn as one integrative-core marker.

No changes to `render/inspector.js`, `render/senses.js`,
`render/population.js`, or any belief-related code path.

## Testing

`observatory/test_morphology.py` (new): shells out to `node` (checked
via `shutil.which("node")`; the whole test class is `unittest.skipUnless`
when absent, so CI without Node doesn't hard-fail) to import and call
`projectPhenotypeMorphology` with fixture inputs, asserting on the
returned JSON per §22/§32:

- same input → byte-identical `boundaryPath` across two separate `node`
  invocations.
- two different `identitySeed`s → different `boundaryPath`.
- `health`/`confidence` differing, same `identitySeed` → same
  `boundaryPath` (they may only modulate presentation, never reseed the
  base shape).
- `edges: []` → `fibres: []` (no fabricated connectivity, regardless of
  `conceptNodes`/`readoutNodes` content).
- `conceptNodes: [], readoutNodes: [], edges: []` (the demo/schema-v1
  shape) → `internalAnchors: [], coreAnchor: null, fibres: []`.
- an edge naming a node id not present in `conceptNodes`/`readoutNodes`
  → silently dropped, not present in `fibres`.

Since morphology.js has zero imports, invocation is a plain
`node --input-type=module -e "import {projectPhenotypeMorphology} from '...'; console.log(JSON.stringify(projectPhenotypeMorphology(INPUT)))"`
per fixture, output parsed as JSON and asserted on from Python — no
package.json, no JS test runner, no new repo-wide dependency; only this
one test file's own skip condition.

`observatory/test_contract.py`: update/add literal-text assertions —
`cellPath` constant must no longer exist anywhere in the frontend
bundle (replaces PR1's `render/organism.js` local-var assertion, if any
existed — there wasn't one, this is new); `phenotypeBoundary`/
`projectPhenotypeMorphology` should be present; existing sense/organism
assertions otherwise unaffected since `render/organism.js` still
exports `renderOrganism` the same way.

## Verification

- `pytest observatory/ -x` green (including the new,
  Node-conditional `test_morphology.py`).
- Manual Playwright pass (same pattern as PR1): serve `observatory/`,
  confirm zero new console errors, confirm demo mode still shows
  boundary + 5 sense receptors + all 25 decorative belief
  circles/lines exactly as before (just inside a generated, not
  hardcoded, boundary), confirm no internal topology regions/fibres
  render in demo (honest 0-topology state). A real schema-v2 fixture
  (recorded replay or live resident, if available) additionally shows
  internal regions/fibres from its actual graph and a differently-shaped
  boundary than demo's.
- Exit condition (§31 Phase 2): two organisms with different
  phenotype/identity visibly differ, without invented structure.
