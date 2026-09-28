# P7 — Browser Rendering Cost

Status: implementation candidate  
Base: P6 SSE transport cleanup on `main`

## Scope

P7 changes only observer-side presentation code under
`symbiont_lab/workbench/web`.

It does not change:

- organism state;
- cognition topology;
- evidence;
- learned relations;
- telemetry contracts;
- observation sampling;
- physics;
- causal provenance.

## 1. Cognition repulsion

The previous 2D and 3D layouts performed explicit pairwise repulsion across the
whole visible graph.

P7 introduces deterministic spatial buckets.

### 2D

Only pairs within the pre-existing local repulsion radius are enumerated through
`forEachNearbyPair2D()`.

The spatial index is exact for that radius: the benchmark compares its pair set
against a brute-force reference and requires identical pair counts.

Graph edges, sector anchors, gravity and affinity links continue to provide
global organization.

### 3D

`forEachNearbyPair3D()` bounds collision/repulsion work to a 288-unit local
neighbourhood.

This is intentionally a presentation approximation. Distant pairwise repulsion
is not scientific evidence and does not belong to Symbiont. Global shape still
comes from:

- real graph-edge attraction;
- component cohesion;
- physicalized compact pressure;
- node inertia.

The resulting geometry remains an observer experiment, not anatomy.

## 2. Incident-edge plasticity

The previous 3D relaxation scanned `edges.filter(...)` twice for every node on
every iteration.

P7 accumulates incident plasticity once per iteration in
`plasticityByNode`, reducing that term from O(N·E) repeated scans to O(E + N).

## 3. Canvas compositing

Canvas shadow blur was enabled for nearly every 2D node, including a default
blur on inactive nodes.

P7 reserves blur for focused/path-connected nodes. Activity, prediction error
and learning remain visible through existing:

- radius;
- alpha;
- error rings;
- pulse rings;
- fMRI overlays;
- relation styling.

The 3D projection follows the same rule.

## 4. RAF versus DOM

The cognition animation loop previously called `updateCognitionSummary()` on
every rendered frame. That function rebuilds the learned observer graph,
derives summary statistics and mutates several DOM panels.

P7 introduces `maybeUpdateCognitionSummary()`.

Canvas animation remains frame-driven, while summary DOM work is refreshed when
its logical key changes and is bounded to a 250 ms refresh window for repeated
identical state.

User actions such as timeline/diff/mode changes can force immediate refresh.

The 3D explanatory note also mutates `textContent` only when its rendered value
changes.

## 5. Body workspace

Body already uses persistent Three.js objects and UI throttling; the older
"rebuild SVG every frame" concern no longer describes current main.

P7 therefore does not replace the renderer. It removes unnecessary workspace
rerenders by ignoring metric updates whose text and color are unchanged.

## Acceptance boundaries

P7 tests prevent:

1. return of explicit all-pairs loops to cognition 2D/3D;
2. return of per-node `edges.filter()` rescans in 3D relaxation;
3. direct full summary rebuilds from each animation frame;
4. default Canvas blur on every node;
5. Body workspace rerendering on unchanged metrics.

`scripts/bench_browser_layout.mjs` compares the deterministic 2D spatial index
against brute-force pair enumeration and reports 2D/3D indexing cost as graph
size grows.

P8 must now reprofile the complete system after P0–P7 rather than assuming the
original CognitiveGraph percentages are still representative.
