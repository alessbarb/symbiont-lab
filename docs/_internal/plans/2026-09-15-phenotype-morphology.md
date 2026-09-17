# Deterministic Phenotype Morphology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `observatory/render/organism.js`'s hardcoded `cellPath` with a deterministic, identity-seeded boundary, and make real cognitive topology (`nodes`/`edges`) actually reach the visual instead of being discarded after computing a text summary.

**Architecture:** A new pure module `projection/morphology.js` turns `{identitySeed, percepts, hasCurrentTopology, structuralSenses, internalNodes, edges, topologyHealth, recovering, frozen}` into SVG geometry (`boundaryPath`, anchors, fibres, presentation hints) via a self-contained deterministic PRNG — no DOM, no imports, testable by shelling out to `node`. Boundary and receptor placement share one Bezier evaluator so a receptor is always exactly on the curve that gets drawn, never an approximation of it. A new `projection/topology.js` normalizes the raw SSE topology payload (real wire field names `node_id`/`source_id`/`target_id`) into the shape morphology consumes, and is the client-side defensive boundary the server itself doesn't provide. `render/organism.js` becomes the only file that reads `state` and calls into morphology; existing belief-circle/attention-ring/dissent-path code stays untouched except that its decorative belief-edge lines are now demo-only.

**Tech Stack:** Vanilla ES modules (no bundler — confirmed absent repo-wide), Python `unittest`/`pytest`, Node (v18+ floor, dev environment has v24) invoked as a subprocess for pure-JS-module tests only, via a `data:` URL import (not a bare file path) so it works identically across that whole version range without a `package.json` — no JS test runner added.

**Spec:** `docs/_internal/specs/2026-09-15-phenotype-morphology-design.md` (final, two review rounds closed). This plan implements it as written; where the spec says "implementation detail for the plan" (exact PRNG/geometry constants), this plan makes the concrete choice.

## Global Constraints

- Zero new backend/schema fields — every input to morphology must already exist in `snapshot.schema.json`/`topology.schema.json`/`cognition_state.schema.json` today.
- `projection/morphology.js` and `projection/topology.js` must have **zero imports** (fully pure, Node-executable in isolation via `node --input-type=module`).
- No `Math.random()` anywhere in morphology — `Math.imul`-based FNV-1a hash + mulberry32 PRNG only, seeded from `identitySeed` (never `topologyRevision`, never array index for anchor positions).
- Coordinates in `boundaryPath`/anchors are quantized (`toFixed(2)`) so output is byte-identical across runs/platforms for the same input.
- `structuralSenses`/`internalNodes`/`edges` are sorted canonically inside `morphology.js` itself (`id` code-point order; edges by `(sourceId, targetId, kind)`) — never rely on caller order.
- Decorative belief-edge lines (`belief[(i+4)%n]` neighbor lines) draw only when `state.source === "demo"` — never for any real organism, with or without topology.
- `state.topology` must be `null`ed on `connectInstance()` instance switch and on `loadReplayFile()` load; `state.cognition` must be assigned before `renderOrganism()` is called in `ingestSnapshot`. On instance switch, the topology-triggered re-render must additionally wait for that instance's own first snapshot (`currentInstanceHasSnapshot`) — resetting `state.topology`/`state.cognition` alone is not enough to prevent a moment of instance-B-boundary-around-instance-A-percepts.
- `morphology.js`'s receptor set is chosen by the explicit `hasCurrentTopology` boolean, never by testing whether `structuralSenses` happens to be empty — a real topology with zero SENSE nodes and the total absence of topology are different states and must not both fall back to percepts.
- Receptor anchors are placed by evaluating the exact same cubic Bezier segment used to build `boundaryPath` (one shared `segmentControlPoints`/`evaluateBoundaryAt` pair) — never a separate radius-interpolation approximation that could disagree with the rendered curve.
- No changes to `render/inspector.js`, `render/senses.js`, `render/population.js`.
- Node-dependent test files (`test_topology.py`, `test_morphology.py`, `test_worker3_fixture.py`) must `unittest.skipUnless(shutil.which("node"), ...)` at the class level — a CI/dev machine without Node must not fail the whole suite. The harness imports each module's source via a `data:text/javascript;base64,...` URL, never a bare file-path `import`, so this works on Node 18 through 24+ without a `package.json`.

---

## File Structure

```
observatory/
├── _node_harness.py                (new — shared Node-subprocess test helper)
├── projection/
│   ├── topology.js                 (new — boundedTopology())
│   └── morphology.js               (new — projectPhenotypeMorphology())
├── render/
│   └── organism.js                 (modified — consumes morphology instead of cellPath)
├── transport/
│   ├── instance-stream.js          (modified — state.instanceId/state.topology wiring + resets)
│   └── replay.js                   (modified — state.topology reset)
├── projection/snapshot.js          (modified — state.cognition ordering + topologyHealth/recovering)
├── styles.css                      (modified — .membrane → .phenotype-boundary rename)
├── test_topology.py                (new)
├── test_morphology.py              (new)
├── test_state_flow.py              (new — ordering/reset contract tests)
├── test_worker3_fixture.py         (new — explicit acceptance fixture)
└── test_contract.py                (modified — cellPath absence, new symbol presence)
```

---

## Task 1: `projection/topology.js` — normalize raw SSE topology

**Files:**

- Create: `observatory/projection/topology.js`
- Create: `observatory/_node_harness.py`
- Test: `observatory/test_topology.py`

**Interfaces:**

- Produces: `boundedTopology(raw)` — pure function; `raw` is whatever `payload.topology` the SSE stream hands the browser (a plain object matching, or violating, `topology.schema.json`); returns `{ genomeId: string, topologyRevision: number, nodes: [{id, kind}], edges: [{sourceId, targetId, kind}] }` or `null`.

- [ ] **Step 1: Write the shared Node-subprocess test harness**

Create `observatory/_node_harness.py`:

```python
"""Shared helper for tests that execute a pure, zero-import Observatory
frontend module via Node, since this repo has no JS test runner/bundler.
Only pure modules (no DOM, no imports) can be called this way.

IMPORTANT: a plain `import "./foo.js"` of an on-disk .js file is only
reliably treated as an ES module by Node's loader without a package.json
declaring "type": "module" on newer Node versions that auto-detect ESM
syntax (stabilized around Node 22-24) -- this repo's floor is Node 18,
where a bare .js import under `--input-type=module` can throw
"Unexpected token 'export'" because the file is parsed as CommonJS. Since
the plan's Global Constraints forbid adding a package.json just for tests,
this harness instead reads the module's source and imports it as a
`data:text/javascript;base64,...` URL -- data: URLs are unambiguously ESM
to Node's loader regardless of extension, package.json, or Node version,
so this works identically on Node 18 through 24+."""
import base64
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
NODE = shutil.which("node")

requires_node = unittest.skipUnless(NODE, "node is not on PATH")


def call_js(module_path: Path, export_name: str, arg) -> object:
    source = module_path.read_text(encoding="utf-8")
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    specifier = f"data:text/javascript;base64,{encoded}"
    script = (
        f"import {{ {export_name} }} from {json.dumps(specifier)};"
        f"const result = {export_name}({json.dumps(arg)});"
        "process.stdout.write(JSON.stringify(result));"
    )
    completed = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"node invocation failed: {completed.stderr}")
    return json.loads(completed.stdout)
```

- [ ] **Step 2: Write the failing tests**

Create `observatory/test_topology.py`:

```python
import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "topology.js"


def bounded(raw):
    return call_js(MODULE, "boundedTopology", raw)


VALID_RAW = {
    "genome_id": "genome-abc",
    "kernel_version": "1.0.0",
    "topology_revision": 3,
    "nodes": [
        {"node_id": "n-sense-1", "kind": "sense", "bias": 0.1, "tau": 1.0},
        {"node_id": "n-concept-1", "kind": "concept", "bias": 0.2, "tau": 2.0},
    ],
    "edges": [
        {"source_id": "n-sense-1", "target_id": "n-concept-1", "kind": "excitatory"},
    ],
}


@requires_node
class BoundedTopologyTests(unittest.TestCase):
    def test_renames_wire_fields_to_normalized_shape(self):
        result = bounded(VALID_RAW)
        self.assertEqual(result["genomeId"], "genome-abc")
        self.assertEqual(result["topologyRevision"], 3)
        self.assertEqual(result["nodes"], [
            {"id": "n-sense-1", "kind": "sense"},
            {"id": "n-concept-1", "kind": "concept"},
        ])
        self.assertEqual(result["edges"], [
            {"sourceId": "n-sense-1", "targetId": "n-concept-1", "kind": "excitatory"},
        ])

    def test_drops_node_with_unknown_kind(self):
        raw = {**VALID_RAW, "nodes": [{"node_id": "x", "kind": "not-a-real-kind", "bias": 0, "tau": 1}]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])

    def test_drops_duplicate_node_id_keeping_the_first(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": "dup", "kind": "sense", "bias": 0, "tau": 1},
            {"node_id": "dup", "kind": "readout", "bias": 0, "tau": 1},
        ]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [{"id": "dup", "kind": "sense"}])

    def test_caps_nodes_at_128(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": f"n{i}", "kind": "sense", "bias": 0, "tau": 1} for i in range(140)
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["nodes"]), 128)

    def test_caps_edges_at_1024(self):
        raw = {**VALID_RAW, "edges": [
            {"source_id": "a", "target_id": "b", "kind": "excitatory"} for _ in range(1100)
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["edges"]), 1024)

    def test_edge_with_unresolvable_endpoint_is_still_kept(self):
        raw = {**VALID_RAW, "edges": [
            {"source_id": "no-such-node", "target_id": "also-missing", "kind": "excitatory"},
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["edges"]), 1)

    def test_missing_genome_id_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "genome_id"}
        self.assertIsNone(bounded(raw))

    def test_missing_or_malformed_input_returns_none(self):
        self.assertIsNone(bounded(None))
        self.assertIsNone(bounded("not an object"))
        self.assertIsNone(bounded({}))

    def test_non_integer_topology_revision_returns_none(self):
        # 3.8 is a float, not the integer the schema requires -- accepting it
        # via a lossy Number.parseInt would be exactly the leniency this
        # function exists to refuse.
        raw = {**VALID_RAW, "topology_revision": 3.8}
        self.assertIsNone(bounded(raw))

    def test_missing_nodes_array_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "nodes"}
        self.assertIsNone(bounded(raw))

    def test_missing_edges_array_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "edges"}
        self.assertIsNone(bounded(raw))

    def test_node_missing_bias_or_tau_is_dropped(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": "no-bias", "kind": "sense", "tau": 1.0},
            {"node_id": "no-tau", "kind": "sense", "bias": 0.1},
        ]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])

    def test_node_with_tau_out_of_range_is_dropped(self):
        raw = {**VALID_RAW, "nodes": [{"node_id": "bad-tau", "kind": "sense", "bias": 0, "tau": 15.0}]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /home/alessbarb/workspace/repos/incubating/symbiont-lab && python3 -m pytest observatory/test_topology.py -v`
Expected: FAIL (or ERROR) — `observatory/projection/topology.js` does not exist yet, so the `node` subprocess errors.

- [ ] **Step 4: Implement `boundedTopology`**

Create `observatory/projection/topology.js`:

```js
const NODE_KINDS = new Set(["sense", "concept", "state", "predictor", "gate", "readout"]);
const EDGE_KINDS = new Set(["excitatory", "inhibitory", "predictive", "gating"]);

function boundedTopology(raw) {
  if (!raw || typeof raw !== "object") return null;
  if (typeof raw.genome_id !== "string" || raw.genome_id.length === 0 || raw.genome_id.length > 72) return null;
  if (typeof raw.kernel_version !== "string" || raw.kernel_version.length === 0 || raw.kernel_version.length > 32) return null;
  if (!Number.isInteger(raw.topology_revision) || raw.topology_revision < 0) return null;
  // topology.schema.json requires nodes/edges as arrays (not optional) --
  // this is the real client-side defensive boundary, since the server only
  // checks isinstance(dict) before forwarding whatever the topology file
  // contains, so a missing/malformed key here must reject the whole payload
  // rather than silently substituting an empty array.
  if (!Array.isArray(raw.nodes) || !Array.isArray(raw.edges)) return null;

  const seenIds = new Set();
  const nodes = [];
  raw.nodes.slice(0, 128).forEach(node => {
    if (!node || typeof node.node_id !== "string" || node.node_id.length === 0 || node.node_id.length > 128) return;
    if (!NODE_KINDS.has(node.kind)) return;
    if (!Number.isFinite(node.bias)) return;
    if (!Number.isFinite(node.tau) || node.tau < 0.1 || node.tau > 10.0) return;
    if (seenIds.has(node.node_id)) return;
    seenIds.add(node.node_id);
    nodes.push({ id: node.node_id, kind: node.kind });
  });

  const edges = [];
  raw.edges.slice(0, 1024).forEach(edge => {
    if (!edge) return;
    const sourceId = edge.source_id;
    const targetId = edge.target_id;
    if (typeof sourceId !== "string" || sourceId.length === 0 || sourceId.length > 128) return;
    if (typeof targetId !== "string" || targetId.length === 0 || targetId.length > 128) return;
    if (!EDGE_KINDS.has(edge.kind)) return;
    edges.push({ sourceId, targetId, kind: edge.kind });
  });

  return { genomeId: raw.genome_id, topologyRevision: raw.topology_revision, nodes, edges };
}

export { boundedTopology };
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_topology.py -v`
Expected: PASS (13 tests), unless `node` is absent from PATH, in which case all skip.

- [ ] **Step 6: Commit**

```bash
cd /home/alessbarb/workspace/repos/incubating/symbiont-lab
git add observatory/_node_harness.py observatory/projection/topology.js observatory/test_topology.py
git commit -m "feat(observatory): add boundedTopology() to normalize raw SSE topology"
```

---

## Task 2: State plumbing — `instanceId`/`topology`/`cognition`, resets, ordering

**Files:**

- Modify: `observatory/state/demo-state.js:53` (`createInitialState`)
- Modify: `observatory/transport/instance-stream.js` (whole file, 24 lines)
- Modify: `observatory/transport/replay.js:25` (`loadReplayFile`)
- Modify: `observatory/projection/snapshot.js:23-40` (`boundedCognition`), `:141-164` (`ingestSnapshot`)
- Test: `observatory/test_state_flow.py`

**Interfaces:**

- Consumes: `boundedTopology` from Task 1 (`observatory/projection/topology.js`).
- Produces: `state.instanceId` (string|null), `state.topology` (normalized shape from Task 1|null), `state.cognition` (now includes `topologyHealth`/`recovering`) — all three read by Task 3/4.

- [ ] **Step 1: Write the failing contract tests**

Create `observatory/test_state_flow.py`:

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class StateFlowTests(unittest.TestCase):
    def test_initial_state_has_topology_cognition_instance_id_fields(self):
        demo_state = read("state", "demo-state.js")
        self.assertIn("topology: null", demo_state)
        self.assertIn("cognition: null", demo_state)
        self.assertIn("instanceId: null", demo_state)

    def test_connect_instance_resets_topology_and_cognition_before_opening_stream(self):
        instance_stream = read("transport", "instance-stream.js")
        reset_topology = instance_stream.index("state.topology = null;")
        reset_cognition = instance_stream.index("state.cognition = null;")
        opens_stream = instance_stream.index("new EventSource(")
        set_instance_id = instance_stream.index("state.instanceId = instanceId;")
        self.assertLess(set_instance_id, opens_stream)
        self.assertLess(reset_topology, opens_stream)
        self.assertLess(reset_cognition, opens_stream)

    def test_instance_stream_stores_bounded_topology_and_rerenders(self):
        instance_stream = read("transport", "instance-stream.js")
        self.assertIn("import { boundedTopology }", instance_stream)
        self.assertIn("state.topology = boundedTopology(payload.topology);", instance_stream)
        self.assertIn("renderCognitionTopology(payload.topology)", instance_stream)
        self.assertIn('if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();', instance_stream)

    def test_instance_stream_gates_topology_render_on_this_instances_own_snapshot(self):
        """A topology(B) message arriving before B's own first snapshot must
        not repaint the organism using A's still-current senses/beliefs --
        the readiness flag must be reset on connect and only flip true once
        this instance's own snapshot branch has actually run."""
        instance_stream = read("transport", "instance-stream.js")
        declaration = instance_stream.index("let currentInstanceHasSnapshot = false;")
        reset_in_connect = instance_stream.index("currentInstanceHasSnapshot = false;", instance_stream.index("function connectInstance"))
        opens_stream = instance_stream.index("new EventSource(")
        set_true = instance_stream.index("currentInstanceHasSnapshot = true;")
        ingest_call = instance_stream.index("ingestSnapshot(payload.snapshot);")
        self.assertLess(declaration, reset_in_connect)
        self.assertLess(reset_in_connect, opens_stream)
        self.assertLess(set_true, ingest_call)

    def test_load_replay_file_resets_topology_before_first_ingest(self):
        replay = read("transport", "replay.js")
        reset_index = replay.index("state.topology = null;")
        ingest_index = replay.index("ingestSnapshot(state.replay[0], false);")
        self.assertLess(reset_index, ingest_index)

    def test_ingest_snapshot_assigns_cognition_before_rendering_organism(self):
        snapshot = read("projection", "snapshot.js")
        cognition_assignment = snapshot.index("state.cognition = projection.cognition;")
        render_organism_call = snapshot.index("renderOrganism();")
        render_cognition_state_call = snapshot.index("renderCognitionState(projection.cognition);")
        self.assertLess(cognition_assignment, render_organism_call)
        self.assertLess(render_organism_call, render_cognition_state_call)

    def test_bounded_cognition_carries_topology_health_and_recovering(self):
        snapshot = read("projection", "snapshot.js")
        start = snapshot.index("function boundedCognition(")
        end = snapshot.index("\nfunction ", start + 1)
        body = snapshot[start:end]
        self.assertIn("topologyHealth", body)
        self.assertIn("recovering", body)
        self.assertIn('cognition.topology_health', body)
        self.assertIn('cognition.recovering', body)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: FAIL on every test (none of the source changes exist yet).

- [ ] **Step 3: Add the three new fields to `createInitialState`**

Edit `observatory/state/demo-state.js` line 53 — add `topology: null, cognition: null, instanceId: null,` into the state object literal (anywhere inside the `{ ... }`, e.g. right after `senseHistory: new Map(),`):

```js
  const state = { view: "individual", mode: "live", playing: true, tick: 18, realTick: null, selected: beliefs[12], replay: [], replayIndex: 0, source: "demo", events: demoEvents, liveEvents: [], eventFilter: "all", query: "", selectedEvent: demoEvents[6], compareA: null, compareB: null, populationMode: "ecology", organismA: null, organismB: null, displayId: null, organismState: "unknown", sensoryDevelopment: [], sensoryRelations: [], sampling: { active: 0, probing: 0, dormant: 0, unknown: 0, sampledThisTick: 0, discovered: 0 }, schemaVersion: 1, senseHistory: new Map(), senses: createDemoSenses(), beliefs, topology: null, cognition: null, instanceId: null };
```

- [ ] **Step 4: Rewrite `transport/instance-stream.js`**

Replace the whole file:

```js
import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";
import { renderOrganism } from "../render/organism.js";
import { boundedTopology } from "../projection/topology.js";

let currentInstanceSource = null;
let currentInstanceId = null;
// Topology and snapshot arrive as two independent SSE messages, in either
// order. If topology(B) is what happens to arrive first after switching
// from instance A, resetting state.topology/state.cognition alone is not
// enough: state.senses/state.beliefs/etc. are still A's until B's own first
// snapshot lands, so re-rendering on that lone topology message would draw
// B's identity/boundary around A's percepts/beliefs -- exactly the
// cross-individual mixing the reset was supposed to prevent. Gate the
// topology-triggered render on this instance's own first snapshot having
// already arrived; ingestSnapshot's own renderOrganism() call (inside
// projection/snapshot.js, unrelated to this file) covers the snapshot-first
// case once the snapshot itself lands.
let currentInstanceHasSnapshot = false;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
  currentInstanceId = instanceId;
  state.instanceId = instanceId;
  state.topology = null;
  state.cognition = null;
  currentInstanceHasSnapshot = false;
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.topology) {
      renderCognitionTopology(payload.topology);
      state.topology = boundedTopology(payload.topology);
      if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();
      return;
    }
    if (payload.snapshot) {
      state.source = "local server";
      document.querySelector("#welcome").hidden = true;
      document.querySelector(".connection strong").textContent = "Connected";
      currentInstanceHasSnapshot = true;
      ingestSnapshot(payload.snapshot);
    }
  };
}

export { currentInstanceSource, currentInstanceId, connectInstance };
```

(This introduces an import cycle — `transport/instance-stream.js` → `render/organism.js` → `projection/morphology.js` (Task 3/4) — but `render/organism.js` does not import `transport/instance-stream.js` back, so it is not actually circular; no special handling needed here, unlike PR1's genuine 3-node cycle.)

- [ ] **Step 5: Add the reset to `transport/replay.js`**

Edit `observatory/transport/replay.js` — insert one line immediately before the existing `ingestSnapshot(state.replay[0], false);` call (currently reached via `state.replay = validateReplay(parsed); ...` a few lines above it):

```js
    state.replay = validateReplay(parsed); state.replayIndex = 0; state.mode = "replay"; state.source = "replay"; state.playing = false;
    document.querySelectorAll(".mode").forEach(button => button.classList.toggle("active", button.dataset.mode === "replay"));
    document.querySelector("#play").classList.add("paused"); document.querySelector("#play").setAttribute("aria-label", "Resume playback");
    state.topology = null;
    ingestSnapshot(state.replay[0], false);
```

- [ ] **Step 6: Reorder `state.cognition` assignment and extend `boundedCognition` in `projection/snapshot.js`**

Edit the `boundedCognition` function (lines 23-40) — add `topologyHealth`/`recovering` to its return:

```js
function boundedCognition(cognition) {
  if (!cognition || typeof cognition !== "object") return null;
  const readouts = {};
  Object.entries(cognition.readouts ?? {}).forEach(([id, value]) => { if (typeof id === "string" && Number.isFinite(Number(value))) readouts[id.slice(0, 128)] = Number(value); });
  const predictionErrors = {};
  Object.entries(cognition.prediction_errors ?? {}).forEach(([id, cls]) => { if (typeof id === "string" && typeof cls === "string") predictionErrors[id.slice(0, 128)] = cls; });
  const mutations = (Array.isArray(cognition.mutations) ? cognition.mutations : []).slice(0, 8).map(item => ({
    kind: typeof item?.kind === "string" ? item.kind : "unknown",
    nodeId: typeof item?.node_id === "string" ? item.node_id.slice(0, 128) : null,
    edgeId: typeof item?.edge_id === "string" ? item.edge_id.slice(0, 260) : null,
  }));
  const safety = cognition.safety_state ?? {};
  const allowedHealth = ["germinal", "developing", "connected", "adaptive", "degenerate", "recovering"];
  const topologyHealth = allowedHealth.includes(cognition.topology_health) ? cognition.topology_health : "germinal";
  return {
    topologyRevision: Math.max(0, Number.parseInt(cognition.topology_revision, 10) || 0),
    topologyHealth,
    recovering: cognition.recovering === true,
    readouts, predictionErrors, mutations,
    safetyState: { consecutiveFailures: Math.max(0, Number.parseInt(safety.consecutive_failures, 10) || 0), frozen: safety.frozen === true },
  };
}
```

Then, inside `ingestSnapshot` (around line 153, right after `state.schemaVersion = projection.schemaVersion;` and before the `state.selected = ...` line), add the cognition assignment, and confirm it now precedes the render calls on the line that already reads `renderSenses(); renderOrganism(); ...`:

```js
  state.sensoryRelations = projection.sensoryRelations;
  state.sampling = projection.sampling;
  state.schemaVersion = projection.schemaVersion;
  state.cognition = projection.cognition;
  // Re-resolve by id against the freshly-ingested beliefs array rather than
  // keeping the previous snapshot's object — that object's certainty/evidence
  // are now stale even when its id still exists in the new collection
  // (roadmap safety finding B07).
  state.selected = state.beliefs.find(item => item.id === state.selected?.id) ?? state.beliefs[0] ?? null;
  if (projection.displayId) { state.displayId = projection.displayId; document.querySelector("#organism-name").textContent = `Organism ${projection.displayId}`; }
  state.organismState = projection.organismState;
  document.querySelector("#organism-state").textContent = projection.organismState[0].toUpperCase() + projection.organismState.slice(1);
  if (announce) document.querySelector(".connection small").textContent = "snapshot stream";
  renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();
  renderCognitionState(projection.cognition);
```

(No other line in `ingestSnapshot` changes — this only inserts the one new assignment line before the pre-existing `renderSenses(); renderOrganism(); ...` line, which already came before `renderCognitionState(...)`.)

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: PASS (7 tests).

- [ ] **Step 8: Run the full existing suite to check for regressions**

Run: `python3 -m pytest observatory/ -x -q`
Expected: all pass (PR1's 59 tests + Task 1's 8 + this task's 6). `render/organism.js` does not yet import `boundedTopology`/anything from Task 3, so this task does not touch it and nothing here should break existing behavior.

- [ ] **Step 9: Commit**

```bash
git add observatory/state/demo-state.js observatory/transport/instance-stream.js observatory/transport/replay.js observatory/projection/snapshot.js observatory/test_state_flow.py
git commit -m "feat(observatory): wire instanceId/topology/cognition state with correct reset/ordering"
```

---

## Task 3: `projection/morphology.js` — the pure phenotype projector

**Files:**

- Create: `observatory/projection/morphology.js`
- Test: `observatory/test_morphology.py`

**Interfaces:**

- Consumes: nothing (zero imports; pure function of its argument object).
- Produces: `projectPhenotypeMorphology({identitySeed, percepts, hasCurrentTopology, structuralSenses, internalNodes, edges, topologyHealth, recovering, frozen})` → `{ boundaryPath: string, externalInputAnchors: [{id,x,y}], receptorAnchors: [{id,kind,x,y}], internalAnchors: [{id,kind,x,y}], fibres: [{sourceId,targetId,kind,x1,y1,x2,y2}], presentation: {boundaryTension,desaturated,reducedMotion} }`. Task 4 (`render/organism.js`) calls this directly. `hasCurrentTopology` (not "is `structuralSenses` empty") is what selects the percept fallback — see the P0 note in the implementation below.

- [ ] **Step 1: Write the failing tests**

Create `observatory/test_morphology.py`:

```python
import math
import re
import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "morphology.js"

BASE_INPUT = {
    "identitySeed": "genome-x:instance-a",
    "percepts": [],
    "hasCurrentTopology": False,
    "structuralSenses": [],
    "internalNodes": [],
    "edges": [],
    "topologyHealth": None,
    "recovering": False,
    "frozen": False,
}


def project(overrides=None):
    payload = {**BASE_INPUT, **(overrides or {})}
    return call_js(MODULE, "projectPhenotypeMorphology", payload)


def parse_path_segments(d):
    """The boundaryPath's M start point plus each cubic segment's c1/c2/end
    are exactly the control points morphology.js used to draw and evaluate
    the curve -- recover them so tests can check the real rendered curve,
    not an approximation of it, without morphology.js exporting anything
    beyond the single projectPhenotypeMorphology function."""
    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", d)]
    start = (numbers[0], numbers[1])
    segments = []
    prev = start
    rest = numbers[2:]
    for i in range(0, len(rest), 6):
        c1 = (rest[i], rest[i + 1])
        c2 = (rest[i + 2], rest[i + 3])
        end = (rest[i + 4], rest[i + 5])
        segments.append((prev, c1, c2, end))
        prev = end
    return segments


def evaluate_cubic(p1, c1, c2, p2, t):
    mt = 1 - t
    x = mt**3 * p1[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p2[0]
    y = mt**3 * p1[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p2[1]
    return (x, y)


def fine_polygon_from_path(d, steps_per_segment=16):
    """A close approximation of the actual rendered cubic curve (not the
    coarse straight-edged polygon of the 10 control points), by sampling
    each real segment many times."""
    segments = parse_path_segments(d)
    polygon = []
    for p1, c1, c2, p2 in segments:
        for i in range(steps_per_segment):
            polygon.append(evaluate_cubic(p1, c1, c2, p2, i / steps_per_segment))
    return polygon


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside


@requires_node
class MorphologyDeterminismTests(unittest.TestCase):
    def test_same_input_produces_byte_identical_boundary(self):
        a = project()
        b = project()
        self.assertEqual(a["boundaryPath"], b["boundaryPath"])

    def test_different_identity_seed_produces_different_boundary(self):
        a = project({"identitySeed": "seed-one"})
        b = project({"identitySeed": "seed-two"})
        self.assertNotEqual(a["boundaryPath"], b["boundaryPath"])

    def test_presentation_inputs_never_change_boundary_or_internal_anchors(self):
        nodes = [{"id": "c1", "kind": "concept"}]
        a = project({"internalNodes": nodes, "topologyHealth": "connected", "recovering": False, "frozen": False})
        b = project({"internalNodes": nodes, "topologyHealth": "degenerate", "recovering": True, "frozen": True})
        self.assertEqual(a["boundaryPath"], b["boundaryPath"])
        self.assertEqual(a["internalAnchors"], b["internalAnchors"])
        self.assertNotEqual(a["presentation"], b["presentation"])

    def test_receptor_anchor_lies_exactly_on_the_rendered_curve(self):
        """Regression test for the bug where receptors were placed via a
        separate radius-interpolation approximation that could disagree
        with the actual cubic Bezier the boundaryPath draws. Recomputes the
        expected point independently, from the path string, using the same
        formula morphology.js uses internally, and asserts exact
        (to quantization) agreement -- not just "close enough"."""
        result = project({"hasCurrentTopology": True, "structuralSenses": [{"id": "only-sense", "kind": "sense"}]})
        segments = parse_path_segments(result["boundaryPath"])
        angle = (math.radians(130) + math.radians(230)) / 2  # single receptor -> arc midpoint
        u = (angle / (2 * math.pi)) % 1
        n = len(segments)
        scaled = u * n
        i = int(scaled) % n
        t = scaled - int(scaled)
        p1, c1, c2, p2 = segments[i]
        expected_x, expected_y = evaluate_cubic(p1, c1, c2, p2, t)
        receptor = result["receptorAnchors"][0]
        self.assertAlmostEqual(receptor["x"], round(expected_x, 2), places=2)
        self.assertAlmostEqual(receptor["y"], round(expected_y, 2), places=2)


@requires_node
class MorphologyStructureTests(unittest.TestCase):
    def test_no_edges_means_no_fibres_regardless_of_nodes(self):
        result = project({
            "hasCurrentTopology": True,
            "structuralSenses": [{"id": "s1", "kind": "sense"}],
            "internalNodes": [{"id": "c1", "kind": "concept"}, {"id": "r1", "kind": "readout"}],
            "edges": [],
        })
        self.assertEqual(result["fibres"], [])

    def test_no_topology_falls_back_to_percepts_for_receptors(self):
        result = project({
            "hasCurrentTopology": False,
            "percepts": [{"id": "p1", "quality": 0.5, "active": True}, {"id": "p2", "quality": 0.9, "active": True}],
            "structuralSenses": [],
        })
        self.assertEqual(len(result["receptorAnchors"]), 2)
        self.assertEqual(result["internalAnchors"], [])
        self.assertEqual(result["fibres"], [])

    def test_current_topology_with_zero_sense_nodes_does_not_fall_back_to_percepts(self):
        """The P0 regression this input exists to prevent: a real, current
        topology that genuinely has no SENSE nodes must render zero
        receptors, never borrow percept ids as fabricated sensory organs."""
        result = project({
            "hasCurrentTopology": True,
            "percepts": [{"id": "p1", "quality": 0.5, "active": True}, {"id": "p2", "quality": 0.9, "active": True}],
            "structuralSenses": [],
            "internalNodes": [{"id": "c1", "kind": "concept"}],
        })
        self.assertEqual(result["receptorAnchors"], [])

    def test_sense_concept_readout_chain_keeps_the_sense_incident_edge(self):
        result = project({
            "hasCurrentTopology": True,
            "structuralSenses": [{"id": "s1", "kind": "sense"}],
            "internalNodes": [{"id": "c1", "kind": "concept"}, {"id": "r1", "kind": "readout"}],
            "edges": [
                {"sourceId": "s1", "targetId": "c1", "kind": "excitatory"},
                {"sourceId": "c1", "targetId": "r1", "kind": "predictive"},
            ],
        })
        edge_pairs = {(f["sourceId"], f["targetId"]) for f in result["fibres"]}
        self.assertIn(("s1", "c1"), edge_pairs)
        self.assertIn(("c1", "r1"), edge_pairs)
        self.assertEqual(len(result["fibres"]), 2)

    def test_edge_naming_an_unknown_id_is_dropped(self):
        result = project({
            "hasCurrentTopology": True,
            "internalNodes": [{"id": "c1", "kind": "concept"}],
            "edges": [{"sourceId": "c1", "targetId": "does-not-exist", "kind": "excitatory"}],
        })
        self.assertEqual(result["fibres"], [])

    def test_readout_nodes_are_real_anchors_not_a_synthetic_centroid(self):
        result = project({"hasCurrentTopology": True, "internalNodes": [
            {"id": "r1", "kind": "readout"}, {"id": "r2", "kind": "readout"},
        ]})
        kinds = [a["kind"] for a in result["internalAnchors"]]
        self.assertEqual(kinds.count("readout"), 2)

    def test_array_order_does_not_affect_output(self):
        senses_a = [{"id": "s1", "kind": "sense"}, {"id": "s2", "kind": "sense"}]
        senses_b = [{"id": "s2", "kind": "sense"}, {"id": "s1", "kind": "sense"}]
        nodes_a = [{"id": "c1", "kind": "concept"}, {"id": "c2", "kind": "concept"}]
        nodes_b = [{"id": "c2", "kind": "concept"}, {"id": "c1", "kind": "concept"}]
        edges_a = [
            {"sourceId": "s1", "targetId": "c1", "kind": "excitatory"},
            {"sourceId": "c1", "targetId": "c2", "kind": "predictive"},
        ]
        edges_b = list(reversed(edges_a))
        result_a = project({"hasCurrentTopology": True, "structuralSenses": senses_a, "internalNodes": nodes_a, "edges": edges_a})
        result_b = project({"hasCurrentTopology": True, "structuralSenses": senses_b, "internalNodes": nodes_b, "edges": edges_b})
        self.assertEqual(result_a, result_b)

    def test_internal_anchors_fall_within_the_generated_boundary_interior(self):
        nodes = [{"id": f"c{i}", "kind": "concept"} for i in range(12)]
        result = project({"identitySeed": "containment-check", "hasCurrentTopology": True, "internalNodes": nodes})
        polygon = fine_polygon_from_path(result["boundaryPath"])
        for anchor in result["internalAnchors"]:
            self.assertTrue(
                point_in_polygon((anchor["x"], anchor["y"]), polygon),
                f"anchor {anchor} outside boundary polygon (sampled from the actual rendered curve)",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest observatory/test_morphology.py -v`
Expected: FAIL/ERROR — `observatory/projection/morphology.js` does not exist.

- [ ] **Step 3: Implement `projection/morphology.js`**

```js
const CENTER = { x: 450, y: 360 };
const VERTICAL_SQUASH = 0.82;
const BOUNDARY_POINTS = 10;
const BASE_RADIUS = 230;
const BOUNDARY_JITTER = 55;
const INTERIOR_MAX_RADIUS = 100; // conservative: worst-case boundary radius is BASE_RADIUS - BOUNDARY_JITTER = 175
const INPUT_ANCHOR_X = 75;
const INPUT_ANCHOR_TOP = 140;
const INPUT_ANCHOR_BOTTOM = 580;
const RECEPTOR_ARC_START = (230 * Math.PI) / 180;
const RECEPTOR_ARC_END = (130 * Math.PI) / 180;

function fnv1aHash(text) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function quantize(value) {
  return Number(value.toFixed(2));
}

function pointOnEllipse(center, angle, radius) {
  return {
    x: quantize(center.x + Math.cos(angle) * radius),
    y: quantize(center.y + Math.sin(angle) * radius * VERTICAL_SQUASH),
  };
}

function generateBoundaryPoints(identitySeed) {
  const rng = mulberry32(fnv1aHash(identitySeed));
  const points = [];
  for (let i = 0; i < BOUNDARY_POINTS; i++) {
    const angle = (i / BOUNDARY_POINTS) * Math.PI * 2;
    const radius = BASE_RADIUS + (rng() * 2 - 1) * BOUNDARY_JITTER;
    points.push(pointOnEllipse(CENTER, angle, radius));
  }
  return points;
}

function segmentControlPoints(points, i) {
  // The exact same p1/c1/c2/p2 quadruple both the rendered SVG path (below)
  // and receptor placement (evaluateBoundaryAt) use -- factored out once so
  // the two can never drift apart into "the curve users see" vs. "the curve
  // receptors think they're on" (the bug this refactor fixes).
  const n = points.length;
  const p0 = points[(i - 1 + n) % n];
  const p1 = points[i];
  const p2 = points[(i + 1) % n];
  const p3 = points[(i + 2) % n];
  return {
    p1,
    p2,
    c1: { x: quantize(p1.x + (p2.x - p0.x) / 6), y: quantize(p1.y + (p2.y - p0.y) / 6) },
    c2: { x: quantize(p2.x - (p3.x - p1.x) / 6), y: quantize(p2.y - (p3.y - p1.y) / 6) },
  };
}

function boundaryPathFromPoints(points) {
  const n = points.length;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < n; i++) {
    const { c1, c2, p2 } = segmentControlPoints(points, i);
    d += ` C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${p2.x} ${p2.y}`;
  }
  return `${d} Z`;
}

function evaluateBoundaryAt(points, u) {
  // u in [0, 1) parameterizes the whole closed curve; since the control
  // points are placed at evenly-spaced angles, u * 2*PI is also this
  // point's angle. Evaluates the exact cubic Bezier for the matching
  // segment -- this is the same curve the SVG `C` command draws, not an
  // approximation of it, so a receptor placed here is guaranteed to lie
  // exactly on the rendered boundary.
  const n = points.length;
  const scaled = (((u % 1) + 1) % 1) * n;
  const i = Math.floor(scaled) % n;
  const t = scaled - Math.floor(scaled);
  const { p1, c1, c2, p2 } = segmentControlPoints(points, i);
  const mt = 1 - t;
  const x = mt ** 3 * p1.x + 3 * mt ** 2 * t * c1.x + 3 * mt * t ** 2 * c2.x + t ** 3 * p2.x;
  const y = mt ** 3 * p1.y + 3 * mt ** 2 * t * c1.y + 3 * mt * t ** 2 * c2.y + t ** 3 * p2.y;
  return { x: quantize(x), y: quantize(y) };
}

function compareStrings(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function placeInterior(identitySeed, nodeId) {
  const rng = mulberry32(fnv1aHash(`${identitySeed}:${nodeId}`));
  const angle = rng() * Math.PI * 2;
  const radius = rng() * INTERIOR_MAX_RADIUS;
  return pointOnEllipse(CENTER, angle, radius);
}

function projectPhenotypeMorphology({
  identitySeed,
  percepts = [],
  hasCurrentTopology = false,
  structuralSenses = [],
  internalNodes = [],
  edges = [],
  topologyHealth = null,
  recovering = false,
  frozen = false,
}) {
  const boundaryPoints = generateBoundaryPoints(identitySeed);
  const boundaryPath = boundaryPathFromPoints(boundaryPoints);

  const sortedStructuralSenses = [...structuralSenses].sort((a, b) => compareStrings(a.id, b.id));
  const sortedInternalNodes = [...internalNodes].sort((a, b) => compareStrings(a.id, b.id));
  const sortedEdges = [...edges].sort((a, b) =>
    compareStrings(a.sourceId, b.sourceId) || compareStrings(a.targetId, b.targetId) || compareStrings(a.kind, b.kind));

  // hasCurrentTopology (not "does structuralSenses happen to be empty") is
  // what decides the fallback: a real graph with zero SENSE nodes must
  // render zero receptors, not silently borrow percept ids as fake organs.
  // Only the *absence* of any current topology falls back to percepts.
  const receptorSource = hasCurrentTopology
    ? sortedStructuralSenses
    : [...percepts].sort((a, b) => compareStrings(a.id, b.id)).map(p => ({ id: p.id, kind: "sense" }));

  const externalInputAnchors = [];
  const receptorAnchors = [];
  const anchorById = new Map();
  const count = receptorSource.length;

  receptorSource.forEach((node, index) => {
    const inputY = count <= 1
      ? (INPUT_ANCHOR_TOP + INPUT_ANCHOR_BOTTOM) / 2
      : INPUT_ANCHOR_TOP + (index * (INPUT_ANCHOR_BOTTOM - INPUT_ANCHOR_TOP)) / (count - 1);
    externalInputAnchors.push({ id: node.id, x: INPUT_ANCHOR_X, y: quantize(inputY) });

    const angle = count <= 1
      ? (RECEPTOR_ARC_START + RECEPTOR_ARC_END) / 2
      : RECEPTOR_ARC_START + (index / (count - 1)) * (RECEPTOR_ARC_END - RECEPTOR_ARC_START);
    const u = angle / (Math.PI * 2);
    const receptorAnchor = { id: node.id, kind: "sense", ...evaluateBoundaryAt(boundaryPoints, u) };
    receptorAnchors.push(receptorAnchor);
    anchorById.set(node.id, receptorAnchor);
  });

  const internalAnchors = sortedInternalNodes.map(node => {
    const anchor = { id: node.id, kind: node.kind, ...placeInterior(identitySeed, node.id) };
    anchorById.set(node.id, anchor);
    return anchor;
  });

  const fibres = [];
  sortedEdges.forEach(edge => {
    const from = anchorById.get(edge.sourceId);
    const to = anchorById.get(edge.targetId);
    if (!from || !to) return;
    fibres.push({ sourceId: edge.sourceId, targetId: edge.targetId, kind: edge.kind, x1: from.x, y1: from.y, x2: to.x, y2: to.y });
  });

  const presentation = {
    boundaryTension: (recovering || topologyHealth === "recovering" || topologyHealth === "degenerate") ? 0.7 : 1,
    desaturated: frozen === true,
    reducedMotion: frozen === true,
  };

  return { boundaryPath, externalInputAnchors, receptorAnchors, internalAnchors, fibres, presentation };
}

export { projectPhenotypeMorphology };
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_morphology.py -v`
Expected: PASS (12 tests). If `test_internal_anchors_fall_within_the_generated_boundary_interior` fails for a particular seed, this means `INTERIOR_MAX_RADIUS` (100) is not conservative enough relative to that seed's minimum boundary radius — lower the constant (e.g. to 80) and rerun; do not weaken the test.

- [ ] **Step 5: Commit**

```bash
git add observatory/projection/morphology.js observatory/test_morphology.py
git commit -m "feat(observatory): add deterministic pure phenotype morphology projector"
```

---

## Task 4: `render/organism.js` integration

**Files:**

- Modify: `observatory/render/organism.js` (whole file, 95 lines → full rewrite)

**Interfaces:**

- Consumes: `projectPhenotypeMorphology` (Task 3), `state.topology`/`state.cognition`/`state.instanceId` (Task 2).
- Produces: `renderOrganism()` — same exported name/signature as before; no other module's imports of it change.

- [ ] **Step 1: Rewrite `observatory/render/organism.js`**

```js
import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";
import { renderInspector } from "./inspector.js";
import { projectPhenotypeMorphology } from "../projection/morphology.js";

function buildIdentitySeed() {
  // Order matters: demo first (no instance/topology concept applies at
  // all); then a live organism whose topology is actually current (the
  // strongest identity available); then an explicit replay (never has
  // instanceId -- the replay format carries no instance concept); then
  // any other live connection that has an instanceId but no topology yet
  // (e.g. schema-v1, or schema-v2 before its first topology message) --
  // this case must NOT fall into the replay branch, or a live real
  // organism's identity would silently ignore its own instanceId, which
  // is the whole reason instanceId was introduced over the non-unique
  // displayId. Final fallback covers any other combination.
  if (state.source === "demo") return "demo";
  if (state.topology && state.instanceId) return `${state.topology.genomeId}:${state.instanceId}`;
  if (state.source === "replay") return `replay:${state.displayId ?? "unknown"}`;
  if (state.instanceId) return `instance:${state.instanceId}`;
  return `${state.source}:${state.displayId ?? "unknown"}`;
}

function buildMorphologyInput() {
  const topologyIsCurrent = Boolean(
    state.topology && state.cognition &&
    state.topology.topologyRevision === state.cognition.topologyRevision
  );
  const structuralSenses = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind === "sense") : [];
  const internalNodes = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind !== "sense") : [];
  const edges = topologyIsCurrent ? state.topology.edges : [];
  return {
    identitySeed: buildIdentitySeed(),
    percepts: state.senses.map(sense => ({ id: sense.id, quality: sense.quality, active: sense.active })),
    hasCurrentTopology: topologyIsCurrent,
    structuralSenses,
    internalNodes,
    edges,
    topologyHealth: state.cognition?.topologyHealth ?? null,
    recovering: state.cognition?.recovering ?? false,
    frozen: state.cognition?.safetyState?.frozen ?? false,
  };
}

function receptorActivityState(perceptById, anchorId) {
  // A structural sense node with no matching dynamic percept (routine once
  // topology has more SENSE nodes than the 32-percept cap, e.g. worker-3's
  // 58) has zero evidence about its current activity -- it must read as
  // "unknown", never default to "active", or Observatory would be
  // fabricating positive activity for senses it has no reading for at all.
  const percept = perceptById.get(anchorId);
  if (!percept) return "unknown";
  return percept.active ? "active" : "inactive";
}

function renderOrganism() {
  const canvas = document.querySelector("#organism-canvas");
  canvas.replaceChildren();
  const defs = svg("defs");
  const radial = svg("radialGradient", { id: "cell-fill" });
  radial.append(svg("stop", { offset: "0", "stop-color": "#17274e", "stop-opacity": ".46" }), svg("stop", { offset: ".75", "stop-color": "#0a2632", "stop-opacity": ".16" }), svg("stop", { offset: "1", "stop-color": "#71e9ba", "stop-opacity": ".08" }));
  defs.append(radial); canvas.append(defs);
  const group = svg("g", { class: "organism-group" });

  const morphology = projectPhenotypeMorphology(buildMorphologyInput());
  const perceptById = new Map(state.senses.map(sense => [sense.id, sense]));
  const sensePositions = new Map(morphology.receptorAnchors.map(anchor => [anchor.id, anchor]));

  morphology.externalInputAnchors.forEach((inputAnchor, index) => {
    const receptorAnchor = morphology.receptorAnchors[index];
    const activityState = receptorActivityState(perceptById, inputAnchor.id);
    const percept = perceptById.get(inputAnchor.id);
    // quality only ever modulates its own receptor's opacity -- never the
    // whole-organism boundary (that would overload a per-reading signal
    // into a body-wide one it was never meant to carry).
    const pathOpacity = activityState === "active"
      ? String(0.35 + (percept?.quality ?? 1) * 0.5)
      : activityState === "inactive" ? ".25" : ".12";
    const midX = (inputAnchor.x + receptorAnchor.x) / 2;
    group.append(svg("path", { d: `M ${inputAnchor.x} ${inputAnchor.y} C ${inputAnchor.x + 85} ${inputAnchor.y}, ${midX} ${receptorAnchor.y}, ${receptorAnchor.x} ${receptorAnchor.y}`, class: "sensor-path", opacity: pathOpacity }));
    group.append(svg("circle", { cx: receptorAnchor.x, cy: receptorAnchor.y, r: 4, class: `phenotype-receptor phenotype-receptor-${activityState}` }));
    const perceivedThisTick = (state.source === "demo")
      ? activityState === "active"
      : (Array.isArray(state.events) && state.events.some(e => e.type === "perception" && (e.id.includes(inputAnchor.id) || e.label.includes(inputAnchor.id) || (percept?.name && e.label.includes(percept.name)))));
    if (perceivedThisTick && !morphology.presentation.reducedMotion) {
      group.append(svg("circle", { cx: receptorAnchor.x, cy: receptorAnchor.y, r: 3.5, class: "sensor-pulse", opacity: "1" }));
    }
  });

  if (Array.isArray(state.sensoryRelations) && state.sensoryRelations.length) {
    state.sensoryRelations.forEach(rel => {
      const posA = sensePositions.get(rel.senseA);
      const posB = sensePositions.get(rel.senseB);
      if (!posA || !posB || rel.samples < 3) return;
      const syncVal = rel.synchronous !== null ? rel.synchronous : 0;
      const absSync = Math.abs(syncVal);
      const confidence = Math.min(1, rel.samples / 25);
      const stroke = syncVal >= 0 ? palette.mint : palette.coral;
      const dash = syncVal < 0 ? "3 3" : "none";
      const midY = (posA.y + posB.y) / 2;
      const arcOffset = 22 * (0.5 + 0.5 * absSync);
      const strokeWidth = (0.7 + absSync * 1.5).toFixed(1);
      const opacity = (0.2 + absSync * 0.6 * confidence).toFixed(2);
      group.append(svg("path", {
        d: `M ${posA.x} ${posA.y} Q ${posA.x - arcOffset} ${midY} ${posB.x} ${posB.y}`,
        fill: "none", stroke, "stroke-width": strokeWidth, "stroke-dasharray": dash, opacity,
      }));
    });
  }

  group.append(svg("path", { d: morphology.boundaryPath, fill: "url(#cell-fill)", class: "phenotype-boundary" }));
  group.append(svg("path", { d: morphology.boundaryPath, class: "phenotype-boundary-inner" }));
  group.classList.toggle("phenotype-frozen", morphology.presentation.desaturated);
  group.style.opacity = String(morphology.presentation.boundaryTension);

  // Fibres drawn before internal-anchor nodes so a fibre's line terminates
  // visually under its endpoint node, not drawn on top of it.
  morphology.fibres.forEach(fibre => {
    group.append(svg("line", { x1: fibre.x1, y1: fibre.y1, x2: fibre.x2, y2: fibre.y2, class: `fibre fibre-${fibre.kind}` }));
  });
  morphology.internalAnchors.forEach(anchor => {
    group.append(svg("circle", { cx: anchor.x, cy: anchor.y, r: anchor.kind === "readout" ? 14 : 8, class: `internal-anchor internal-anchor-${anchor.kind}` }));
  });

  if (state.source === "demo") {
    state.beliefs.forEach((belief, index) => {
      const neighbor = state.beliefs[(index + 4) % state.beliefs.length];
      group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
    });
  }

  let focus = null;
  if (state.source === "demo") {
    focus = state.beliefs.length ? state.beliefs[(state.tick + 7) % state.beliefs.length] : null;
  } else if (Array.isArray(state.events) && state.events.length) {
    const attentionEvent = state.events.find(e => e.type === "attention");
    if (attentionEvent) {
      const targetId = attentionEvent.belief_id ?? attentionEvent.beliefId;
      if (targetId) {
        focus = state.beliefs.find(b => b.id === targetId || b.id.slice(0, 64) === targetId.slice(0, 64));
      }
      if (!focus && attentionEvent.label) {
        const match = attentionEvent.label.match(/(?:signal|belief|sense)[._a-zA-Z0-9]+/);
        if (match) {
          focus = state.beliefs.find(b => b.id.includes(match[0]) || b.title.includes(match[0]));
        }
      }
    }
  }
  if (focus) {
    group.append(svg("path", { d: `M ${focus.x} ${focus.y} Q 470 365 555 430`, class: "dissent-path", opacity: focus.dissent ? "1" : ".35" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 30, class: "attention-ring" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 16, class: "attention-ring" }));
  }

  state.beliefs.forEach(belief => {
    const node = svg("circle", { cx: belief.x, cy: belief.y, r: belief.r, class: `belief-node${state.selected?.id === belief.id ? " selected" : ""}`, opacity: belief.certainty });
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderOrganism(); document.querySelector(".inspector").classList.add("open"); });
    group.append(node);
  });
  canvas.append(group);
}

export { renderOrganism };
```

- [ ] **Step 2: Run the full observatory suite**

Run: `python3 -m pytest observatory/ -x -q`
Expected: everything from Tasks 1-3 plus PR1's suite still passes — `test_contract.py` has not been updated yet, so its `cellPath`/`membrane` assertions are expected to be **absent already** (that test never asserted `cellPath`'s *presence*, only checked other things), but re-run now to confirm nothing regressed before Task 6 adds the new assertions.

- [ ] **Step 3: Manual smoke check (defer full Playwright pass to Task 8)**

Run: `python3 -m http.server 8787 --directory observatory &` then open `http://127.0.0.1:8787/` in a browser or via Playwright `browser_navigate` — confirm the page loads with **zero console errors** (an import path typo here would 404 silently and leave the canvas blank). Kill the server after confirming (`pkill -f "http.server 8787"`).

- [ ] **Step 4: Commit**

```bash
git add observatory/render/organism.js
git commit -m "feat(observatory): render organism via deterministic phenotype morphology"
```

---

## Task 5: `styles.css` — `.membrane` → `.phenotype-boundary` rename

**Files:**

- Modify: `observatory/styles.css:92-93`

**Interfaces:** none (pure CSS, no JS/Python interface).

- [ ] **Step 1: Rename the selectors**

Edit `observatory/styles.css` lines 92-93 from:

```css
.membrane { fill: rgba(52, 198, 166, .055); stroke: var(--mint); stroke-width: 2; filter: drop-shadow(0 0 10px rgba(113,233,186,.4)); }
.membrane-inner { fill: none; stroke: rgba(113,233,186,.32); stroke-width: 8; stroke-dasharray: 1 8; }
```

to:

```css
.phenotype-boundary { fill: rgba(52, 198, 166, .055); stroke: var(--mint); stroke-width: 2; filter: drop-shadow(0 0 10px rgba(113,233,186,.4)); }
.phenotype-boundary-inner { fill: none; stroke: rgba(113,233,186,.32); stroke-width: 8; stroke-dasharray: 1 8; }
```

Also add styling for the two new element classes `render/organism.js` now emits (`internal-anchor`/`internal-anchor-<kind>`, `fibre`/`fibre-<kind>`) — insert immediately after the renamed rules:

```css
.internal-anchor { fill: rgba(167,119,255,.14); stroke: var(--violet); stroke-width: 1.4; }
.internal-anchor-readout { fill: rgba(80,217,255,.18); stroke: var(--cyan); stroke-width: 2; }
.fibre { stroke: rgba(167,119,255,.5); stroke-width: 1; }
.fibre-inhibitory { stroke: rgba(255,127,131,.5); stroke-dasharray: 2 3; }
.fibre-gating { stroke: rgba(255,189,84,.5); stroke-dasharray: 1 4; }
.phenotype-frozen { filter: grayscale(.6); }
.phenotype-receptor { stroke-width: 1.2; }
.phenotype-receptor-active { fill: var(--cyan); stroke: #cdefff; }
.phenotype-receptor-inactive { fill: rgba(82,112,143,.4); stroke: #52708f; }
.phenotype-receptor-unknown { fill: none; stroke: rgba(82,112,143,.5); stroke-dasharray: 1 2; }
```

(All three `presentation` fields are now applied in Task 4: `.phenotype-frozen` and the `organism-group`'s inline `opacity` from `desaturated`/`boundaryTension`, and `reducedMotion` gates whether the perception pulse circle is drawn at all — the only animation-adjacent element PR2 has. This is deliberately minimal beyond that; elaborate presentation styling is not part of PR2's scope.)

- [ ] **Step 2: Verify no other file still references the old class names**

Run: `grep -rn "membrane" observatory/ --include=*.js --include=*.css --include=*.html`
Expected: no matches (Task 4 already emits `phenotype-boundary`/`phenotype-boundary-inner`, and this is the only CSS file).

- [ ] **Step 3: Commit**

```bash
git add observatory/styles.css
git commit -m "style(observatory): rename .membrane to .phenotype-boundary, style new anchors/fibres"
```

---

## Task 6: `test_contract.py` updates

**Files:**

- Modify: `observatory/test_contract.py`

**Interfaces:** none new — this task only updates test assertions to match Tasks 1-5's deliverables.

- [ ] **Step 1: Add the new assertions**

Add a new test method to the `ObservatoryContractTests` class in `observatory/test_contract.py` (e.g. after `test_frontend_has_a_v1_v2_snapshot_normalizer`):

```python
    def test_cell_path_is_gone_and_morphology_projector_is_wired_in(self) -> None:
        bundle = _read_js_bundle()
        self.assertNotIn("cellPath", bundle)
        self.assertNotIn(".membrane", (ROOT / "styles.css").read_text(encoding="utf-8"))
        organism_js = (ROOT / "render" / "organism.js").read_text(encoding="utf-8")
        morphology_js = (ROOT / "projection" / "morphology.js").read_text(encoding="utf-8")
        topology_js = (ROOT / "projection" / "topology.js").read_text(encoding="utf-8")
        self.assertIn("import { projectPhenotypeMorphology }", organism_js)
        self.assertIn("function projectPhenotypeMorphology(", morphology_js)
        self.assertIn("function boundedTopology(", topology_js)
        self.assertIn(".phenotype-boundary", (ROOT / "styles.css").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run the whole contract test file**

Run: `python3 -m pytest observatory/test_contract.py -v`
Expected: all tests pass, including the new one.

- [ ] **Step 3: Commit**

```bash
git add observatory/test_contract.py
git commit -m "test(observatory): assert cellPath is gone and morphology/topology are wired in"
```

---

## Task 7: Worker-3 acceptance fixture

**Files:**

- Test: `observatory/test_worker3_fixture.py`

**Interfaces:**

- Consumes: `projectPhenotypeMorphology` (Task 3).

- [ ] **Step 1: Write the fixture test**

Create `observatory/test_worker3_fixture.py`:

```python
import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "morphology.js"


def build_worker3_topology():
    structural_senses = [{"id": f"sense-{i:02d}", "kind": "sense"} for i in range(58)]
    internal_nodes = [{"id": f"concept-{i}", "kind": "concept"} for i in range(5)]
    internal_nodes.append({"id": "readout-0", "kind": "readout"})
    return structural_senses, internal_nodes


@requires_node
class Worker3FixtureTests(unittest.TestCase):
    def test_58_sense_5_concept_1_readout_0_edges_renders_honestly(self) -> None:
        """§33 worker-3 validation protocol: 58 SENSE, 5 CONCEPT, 1 READOUT,
        0 edges must become 58 receptors, 6 internal regions, and zero
        fibres -- Observatory must not invent connectivity to fill the
        visual gap left by a genuinely disconnected graph."""
        structural_senses, internal_nodes = build_worker3_topology()
        result = call_js(MODULE, "projectPhenotypeMorphology", {
            "identitySeed": "worker-3-genome:worker-3-instance",
            "percepts": [],
            "hasCurrentTopology": True,
            "structuralSenses": structural_senses,
            "internalNodes": internal_nodes,
            "edges": [],
            "topologyHealth": "connected",
            "recovering": False,
            "frozen": False,
        })
        self.assertEqual(len(result["receptorAnchors"]), 58)
        self.assertEqual(len(result["internalAnchors"]), 6)
        self.assertEqual(
            sum(1 for a in result["internalAnchors"] if a["kind"] == "readout"), 1
        )
        self.assertEqual(
            sum(1 for a in result["internalAnchors"] if a["kind"] == "concept"), 5
        )
        self.assertEqual(result["fibres"], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest observatory/test_worker3_fixture.py -v`
Expected: PASS (or skip if Node absent). This exercises Task 3's code with no changes needed — it is a pure fixture/assertion addition.

- [ ] **Step 3: Commit**

```bash
git add observatory/test_worker3_fixture.py
git commit -m "test(observatory): add worker-3 (58 sense/5 concept/1 readout/0 edge) acceptance fixture"
```

---

## Task 8: Full regression + manual Playwright verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the entire repository test suite**

Run: `cd /home/alessbarb/workspace/repos/incubating/symbiont-lab && python3 -m pytest -q`
Expected: all tests pass (PR1's baseline + every test added in Tasks 1, 2, 3, 6, 7).

- [ ] **Step 2: Serve Observatory and open it**

Run: `python3 -m http.server 8787 --directory observatory &`
Then use the Playwright MCP tools: `browser_navigate` to `http://127.0.0.1:8787/`, then `browser_console_messages` with `level: "error"`.
Expected console errors: at most the two pre-existing/expected ones from PR1's verification (`/fleet` 404 — plain static server has no SSE endpoint; `favicon.ico` 404). Any error naming a `projection/`, `render/`, or `transport/` file path is a real regression — stop and fix before continuing.

- [ ] **Step 3: Walk the demo-mode visual checklist**

Via `browser_snapshot`/`browser_click` (same pattern as PR1's verification): click "Use demo" to dismiss the welcome overlay, confirm the individual organism view shows a boundary (no longer the old fixed hand-drawn silhouette — it will look different every time this plan is implemented against a fresh identity, but consistent across reloads of the same session), 5 persistent `.phenotype-receptor` marks (not just sensor-path curves) with `-active`/`-inactive` styling matching each demo sense's `active` flag (demo's 5 senses all have concrete `active` values, so none should render as `-unknown`), all 25 decorative belief circles **and** belief-edge lines (demo still shows them per the spec's demo-only rule), and confirm **no internal-anchor circles or fibre lines** are present (demo never has topology). Click a sense row and a belief node to confirm `renderInspector()`/`renderOrganism()` still fire without console errors, matching PR1's existing coverage.

- [ ] **Step 4: If a live schema-v2 resident or topology fixture is available, verify the real-topology path**

If a real resident with an actual genome/graph can be started (e.g. via `symbiont-lab organism run` wired to `observatory/resident.py`, or by hand-posting a topology file into a temp `observatory_dir`'s `instances/<id>.topology.json` and connecting `server.py` to it), connect to it in the Observatory UI and confirm: internal-anchor circles and (if the fixture has edges) fibre lines appear; belief-edge decorative lines are **absent** (real organism, not demo); the boundary shape differs from demo's; and — if the fixture approximates worker-3's shape (many more SENSE nodes than the 32-percept cap) — that all structural receptors are actually visible as `.phenotype-receptor` marks around the boundary (not just the ones with a matching percept), and that receptors with no matching percept render as `.phenotype-receptor-unknown`, never falsely `-active`. If no such fixture is readily available in this environment, explicitly note in the final report that this path was verified only by Task 3's/Task 7's automated Node-subprocess tests, not by an end-to-end live browser session — do not claim an end-to-end visual check that didn't happen.

- [ ] **Step 5: Clean up**

```bash
pkill -f "http.server 8787"
rm -rf .playwright-mcp
git status --short
```

Expected: working tree clean except for the commits already made in Tasks 1-7 — nothing left uncommitted, no stray Playwright debug artifacts (matches PR1's own cleanup step).

- [ ] **Step 6: Final confirmation**

No commit in this task (verification-only) — if Steps 1-4 all pass, PR2 is complete and matches the spec's exit condition and worker-3 acceptance fixture.
