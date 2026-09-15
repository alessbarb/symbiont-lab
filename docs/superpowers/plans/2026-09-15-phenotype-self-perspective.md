# Phenotype/Self Perspective Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Individual-view Phenotype/Self sub-toggle to Observatory, with a single centralized render dispatcher (`renderIndividualPerspective()`) as the only place that decides which to draw — replacing all six existing direct `renderOrganism()` call sites.

**Architecture:** A new pure `projection/self-schema.js` module projects `bodySchema` (always `null` in this PR) into an `{state, parts, dependencies}` contract; a new `render/self.js` draws its `undeveloped` message into a new `#self-panel`; a new `render/individual.js` is the sole reader of `state.organismView`, dispatching to `renderOrganism()` or `renderSelf()`. Every prior direct caller of `renderOrganism()` (boot, `switchView`, `advance`, `ingestSnapshot`, the topology SSE handler, and two click handlers) is rewired to call `renderIndividualPerspective()` instead, so Self actually re-renders on every state change PR5 will later feed it — not just on toggle clicks.

**Tech Stack:** Vanilla ES modules (no bundler, no build step — unchanged from PR1/PR2), Python `unittest`/`pytest`, Node subprocess via the existing `observatory/_node_harness.py` (added in PR2) for `projection/self-schema.js`'s pure-function tests.

**Spec:** `docs/superpowers/specs/2026-09-15-phenotype-self-perspective-design.md` (final, one review round closed).

## Global Constraints

- No `adapter.py`, schema, or any Python/backend changes — this plan touches only `observatory/*.js`, `observatory/*.html`, `observatory/*.css`, and `observatory/test_*.py`.
- `projection/self-schema.js` has zero imports (pure).
- `render/self.js` never reads `state.topology`, `state.cognition`, `state.senses`, or `state.beliefs` — enforced by a string-absence test.
- `render/individual.js`'s `renderIndividualPerspective()` is the **only** place in the codebase that reads `state.organismView` to decide what to render. No other module gets an `if (state.organismView === ...)` branch of its own.
- No call site keeps a redundant `if (state.view === "individual")` guard around a call to `renderIndividualPerspective()` — the function has its own guard; duplicating it at call sites is exactly the kind of per-site decision-making this PR eliminates.
- The `render/organism.js` ↔ `render/individual.js` import cycle is safe under the same rule PR1 established: only reference hoisted `function` declarations from a cycle partner, never a top-level `const`/`let`, and never call an imported function during module evaluation (only later, from event handlers).
- `projectSelfSchema` never infers `"developed"` from mere truthiness of its argument — a `{}` input must still yield `"undeveloped"`.
- `state.bodySchema` is `null`, not simply absent/`undefined`, on the initial state object.

---

## File Structure

```
observatory/
├── projection/
│   └── self-schema.js         (new — projectSelfSchema())
├── render/
│   ├── self.js                 (new — renderSelf())
│   └── individual.js           (new — renderIndividualPerspective())
├── state/demo-state.js         (modified — organismView, bodySchema fields)
├── index.html                  (modified — toggle markup, #self-panel)
├── styles.css                  (modified — toggle/self-panel CSS)
├── ui/controls.js              (modified — switchOrganismView, applyIndividualCanvasVisibility, call-site rewiring)
├── app.js                      (modified — boot render swap, organismView restore)
├── projection/snapshot.js      (modified — one call-site swap)
├── transport/instance-stream.js (modified — one call-site swap)
├── render/organism.js          (modified — import + one call-site swap)
├── render/senses.js            (modified — import + one call-site swap)
├── test_self_schema.py         (new)
├── test_contract.py            (modified)
└── test_state_flow.py          (modified — new assertions + 2 corrected pre-existing ones)
```

---

## Task 1: `projection/self-schema.js`

**Files:**
- Create: `observatory/projection/self-schema.js`
- Test: `observatory/test_self_schema.py`

**Interfaces:**
- Produces: `projectSelfSchema(bodySchema)` — pure function; returns `{state: "undeveloped", parts: [], dependencies: []}` for any falsy or truthy-but-not-yet-meaningful input (PR3 never passes anything but `null`). Task 3 (`render/self.js`) consumes this.

- [ ] **Step 1: Write the failing tests**

Create `observatory/test_self_schema.py`:

```python
import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "self-schema.js"


def project(body_schema):
    return call_js(MODULE, "projectSelfSchema", body_schema)


@requires_node
class SelfSchemaTests(unittest.TestCase):
    def test_null_input_is_undeveloped(self):
        result = project(None)
        self.assertEqual(result, {"state": "undeveloped", "parts": [], "dependencies": []})

    def test_empty_object_input_is_still_undeveloped(self):
        # Regression guard: a truthy-but-empty bodySchema must not be
        # mistaken for "developed" just because it isn't null.
        result = project({})
        self.assertEqual(result["state"], "undeveloped")

    def test_module_has_zero_imports(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/alessbarb/workspace/repos/incubating/symbiont-lab && python3 -m pytest observatory/test_self_schema.py -v`
Expected: FAIL/ERROR — `observatory/projection/self-schema.js` does not exist yet.

- [ ] **Step 3: Implement `projection/self-schema.js`**

```js
function projectSelfSchema(bodySchema) {
  if (!bodySchema) {
    return { state: "undeveloped", parts: [], dependencies: [] };
  }
  // bodySchema's wire shape is not part of PR3's contract -- PR3 never
  // passes anything but null/undefined here (state.bodySchema is always
  // null in this PR; there is no PR4 yet to ever set it otherwise). This
  // branch exists only so the function's signature is forward-shaped for
  // PR5, which will replace this body with real state/kind discrimination
  // once BodySchema's actual exported shape exists -- it deliberately
  // does NOT infer "developed" from mere truthiness, since a
  // truthy-but-empty or malformed bodySchema is not evidence of a
  // developed self-model.
  return { state: "undeveloped", parts: [], dependencies: [] };
}

export { projectSelfSchema };
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_self_schema.py -v`
Expected: PASS (3 tests), unless `node` is absent from PATH, in which case the two `@requires_node` tests skip (the zero-imports test still runs — it's plain Python, no `@requires_node` decorator needed since it doesn't invoke Node).

- [ ] **Step 5: Commit**

```bash
cd /home/alessbarb/workspace/repos/incubating/symbiont-lab
git add observatory/projection/self-schema.js observatory/test_self_schema.py
git commit -m "feat(observatory): add projectSelfSchema() self-schema projector"
```

---

## Task 2: `state.organismView`/`state.bodySchema` fields

**Files:**
- Modify: `observatory/state/demo-state.js:53` (`createInitialState`)
- Modify: `observatory/test_state_flow.py`

**Interfaces:**
- Produces: `state.organismView` (`"phenotype"` initially), `state.bodySchema` (`null`) — consumed by Task 6's `render/individual.js` and Task 7's `switchOrganismView`.

- [ ] **Step 1: Write the failing test**

Add to `observatory/test_state_flow.py`'s `StateFlowTests` class (after the existing `test_initial_state_has_topology_cognition_instance_id_fields` method):

```python
    def test_initial_state_has_organism_view_and_body_schema_fields(self):
        demo_state = read("state", "demo-state.js")
        self.assertIn('organismView: "phenotype"', demo_state)
        self.assertIn("bodySchema: null", demo_state)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest observatory/test_state_flow.py::StateFlowTests::test_initial_state_has_organism_view_and_body_schema_fields -v`
Expected: FAIL — the fields don't exist yet.

- [ ] **Step 3: Add the fields**

Edit `observatory/state/demo-state.js` line 53 — the `createInitialState` state object literal currently ends `..., senses: createDemoSenses(), beliefs, topology: null, cognition: null, instanceId: null };`. Change it to:

```js
  const state = { view: "individual", mode: "live", playing: true, tick: 18, realTick: null, selected: beliefs[12], replay: [], replayIndex: 0, source: "demo", events: demoEvents, liveEvents: [], eventFilter: "all", query: "", selectedEvent: demoEvents[6], compareA: null, compareB: null, populationMode: "ecology", organismA: null, organismB: null, displayId: null, organismState: "unknown", sensoryDevelopment: [], sensoryRelations: [], sampling: { active: 0, probing: 0, dormant: 0, unknown: 0, sampledThisTick: 0, discovered: 0 }, schemaVersion: 1, senseHistory: new Map(), senses: createDemoSenses(), beliefs, topology: null, cognition: null, instanceId: null, organismView: "phenotype", bodySchema: null };
```

(Only the trailing `, organismView: "phenotype", bodySchema: null` is new — everything before it is unchanged.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: PASS (all tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add observatory/state/demo-state.js observatory/test_state_flow.py
git commit -m "feat(observatory): add state.organismView and state.bodySchema fields"
```

---

## Task 3: Markup and CSS

**Files:**
- Modify: `observatory/index.html:41-54` (`.canvas-wrap` section)
- Modify: `observatory/styles.css:84` (near `.population-tools`)
- Modify: `observatory/test_contract.py`

**Interfaces:**
- Produces: DOM elements `#organism-view-toggle` (with two `.organism-view-option` buttons, `data-organism-view="phenotype"|"self"`), `#self-panel`. Consumed by Task 4 (`render/self.js` queries `#self-panel`), Task 7 (`ui/controls.js` queries all three).

- [ ] **Step 1: Write the failing test**

Add to `observatory/test_contract.py`'s `ObservatoryContractTests` class (after `test_cell_path_is_gone_and_morphology_projector_is_wired_in`):

```python
    def test_phenotype_self_toggle_markup_exists(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="organism-view-toggle"', index)
        self.assertIn('data-organism-view="phenotype"', index)
        self.assertIn('data-organism-view="self"', index)
        self.assertIn('id="self-panel"', index)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest observatory/test_contract.py::ObservatoryContractTests::test_phenotype_self_toggle_markup_exists -v`
Expected: FAIL.

- [ ] **Step 3: Add the markup**

Edit `observatory/index.html`. Insert this new block immediately after the existing `#population-tools` block (after line 45, before the `<svg id="organism-canvas" ...>` line):

```html
          <div id="organism-view-toggle" class="organism-view-toggle" aria-label="Individual view perspective">
            <button class="organism-view-option active" data-organism-view="phenotype" aria-pressed="true">Phenotype</button>
            <button class="organism-view-option" data-organism-view="self" aria-pressed="false">Self</button>
          </div>
```

Insert this new element immediately after the `<svg id="population-canvas" ...>` line (currently line 47, before `<div class="canvas-legend" ...>`):

```html
          <div id="self-panel" class="self-panel hidden"></div>
```

The `.canvas-wrap` section's relevant lines should now read (in order): `.canvas-heading`, `#population-tools`, the new `#organism-view-toggle`, `#organism-canvas`, `#population-canvas`, the new `#self-panel`, `.canvas-legend`.

- [ ] **Step 4: Add the CSS**

Edit `observatory/styles.css`. Insert immediately after the existing `.population-tools`/`.population-mode` rule (line 84):

```css
.organism-view-toggle { position:absolute; z-index:4; top:20px; left:50%; transform:translateX(-50%); display:flex; border:1px solid var(--line); border-radius:9px; padding:3px; background:rgba(5,18,31,.88); }.organism-view-option { border:0; border-radius:6px; padding:7px 13px; background:transparent; color:var(--muted); font-size:10px; cursor:pointer; }.organism-view-option.active { color:white; background:#0f3a57; box-shadow:inset 0 0 0 1px rgba(80,217,255,.4); }
.self-panel { width: 100%; height: 100%; box-sizing: border-box; padding: 90px 60px 0; }.self-panel h2 { margin: 0 0 12px; font-size: 20px; font-weight: 520; color: var(--text); }.self-panel p { margin: 0 0 10px; color: var(--muted); font-size: 13px; line-height: 1.6; max-width: 520px; }
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m pytest observatory/test_contract.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add observatory/index.html observatory/styles.css observatory/test_contract.py
git commit -m "feat(observatory): add Phenotype/Self toggle and self-panel markup"
```

---

## Task 4: `render/self.js`

**Files:**
- Create: `observatory/render/self.js`
- Modify: `observatory/test_contract.py`

**Interfaces:**
- Consumes: `projectSelfSchema` (Task 1), `#self-panel` (Task 3).
- Produces: `renderSelf()` — consumed by Task 5 (`render/individual.js`).

- [ ] **Step 1: Write the failing tests**

Add to `observatory/test_contract.py`'s `ObservatoryContractTests` class:

```python
    def test_render_self_exists_and_shows_undeveloped_message(self) -> None:
        self_js = (ROOT / "render" / "self.js").read_text(encoding="utf-8")
        self.assertIn("function renderSelf(", self_js)
        self.assertIn("Body schema not yet developed", self_js)
        self.assertIn('import { projectSelfSchema }', self_js)

    def test_render_self_never_reads_privileged_phenotype_state(self) -> None:
        """Self rendering must not consume privileged phenotype state --
        the epistemic boundary Research Invariant I1 exists to protect."""
        self_js = (ROOT / "render" / "self.js").read_text(encoding="utf-8")
        for forbidden in ("state.topology", "state.cognition", "state.senses", "state.beliefs"):
            self.assertNotIn(forbidden, self_js)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest observatory/test_contract.py::ObservatoryContractTests::test_render_self_exists_and_shows_undeveloped_message -v`
Expected: FAIL — `observatory/render/self.js` does not exist yet.

- [ ] **Step 3: Implement `render/self.js`**

```js
import { projectSelfSchema } from "../projection/self-schema.js";

function renderSelf() {
  const panel = document.querySelector("#self-panel");
  const projection = projectSelfSchema(null);
  panel.replaceChildren();
  const heading = document.createElement("h2");
  const body = document.createElement("p");
  const scope = document.createElement("p");
  if (projection.state === "undeveloped") {
    heading.textContent = "Body schema not yet developed";
    body.textContent = "This organism does not yet export a model of its own body. Once available, this view will show only what the organism itself believes about its parts and their relationships — never reconstructed from what Observatory can otherwise observe.";
    scope.textContent = "This central view contains only organism-owned self-knowledge. Surrounding Observatory panels remain external scientific instrumentation.";
  }
  panel.append(heading, body, scope);
}

export { renderSelf };
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_contract.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add observatory/render/self.js observatory/test_contract.py
git commit -m "feat(observatory): add renderSelf() undeveloped-state panel"
```

---

## Task 5: `render/individual.js`

**Files:**
- Create: `observatory/render/individual.js`
- Modify: `observatory/test_contract.py`

**Interfaces:**
- Consumes: `renderOrganism` (`render/organism.js`, existing, unchanged), `renderSelf` (Task 4), `state.view`/`state.organismView` (Task 2).
- Produces: `renderIndividualPerspective()` — the sole entrypoint Task 6 rewires every call site to use.

- [ ] **Step 1: Write the failing test**

Add to `observatory/test_contract.py`'s `ObservatoryContractTests` class:

```python
    def test_render_individual_perspective_is_the_single_dispatcher(self) -> None:
        individual_js = (ROOT / "render" / "individual.js").read_text(encoding="utf-8")
        self.assertIn("function renderIndividualPerspective(", individual_js)
        self.assertIn('if (state.view !== "individual") return;', individual_js)
        self.assertIn('if (state.organismView === "self") renderSelf(); else renderOrganism();', individual_js)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest observatory/test_contract.py::ObservatoryContractTests::test_render_individual_perspective_is_the_single_dispatcher -v`
Expected: FAIL — `observatory/render/individual.js` does not exist yet.

- [ ] **Step 3: Implement `render/individual.js`**

```js
import { state } from "../state/store.js";
import { renderOrganism } from "./organism.js";
import { renderSelf } from "./self.js";

function renderIndividualPerspective() {
  if (state.view !== "individual") return;
  if (state.organismView === "self") renderSelf(); else renderOrganism();
}

export { renderIndividualPerspective };
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest observatory/test_contract.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add observatory/render/individual.js observatory/test_contract.py
git commit -m "feat(observatory): add renderIndividualPerspective() single dispatcher"
```

---

## Task 6: Rewire all six `renderOrganism()` call sites

**Files:**
- Modify: `observatory/app.js`
- Modify: `observatory/ui/controls.js:12-33`
- Modify: `observatory/projection/snapshot.js:168`
- Modify: `observatory/transport/instance-stream.js:39`
- Modify: `observatory/render/organism.js:1-3,158`
- Modify: `observatory/render/senses.js:1-4,57`
- Modify: `observatory/test_state_flow.py` (2 pre-existing assertions must be corrected, not just new ones added — see Step 1)

**Interfaces:**
- Consumes: `renderIndividualPerspective` (Task 5).
- Produces: nothing new — this task only changes *what* six existing call sites call, not any interface.

This is the task that actually builds the seam described in the spec's "The single Individual-perspective entrypoint" section. **Two existing tests in `test_state_flow.py` assert the literal old `renderOrganism()` call text and will fail once this task's code changes land — they must be corrected in this same task, not left broken**: `test_instance_stream_stores_bounded_topology_and_rerenders` (asserts the exact old topology-handler line) and `test_ingest_snapshot_assigns_cognition_before_rendering_organism` (asserts `snapshot.index("renderOrganism();")`).

- [ ] **Step 1: Write the failing tests (new assertions + corrections to 2 existing ones)**

In `observatory/test_state_flow.py`, replace the existing `test_instance_stream_stores_bounded_topology_and_rerenders` method body's last line —

```python
        self.assertIn('if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();', instance_stream)
```

— with:

```python
        self.assertIn("if (currentInstanceHasSnapshot) renderIndividualPerspective();", instance_stream)
```

Replace the existing `test_ingest_snapshot_assigns_cognition_before_rendering_organism` method entirely with:

```python
    def test_ingest_snapshot_assigns_cognition_before_rendering_individual_perspective(self):
        snapshot = read("projection", "snapshot.js")
        cognition_assignment = snapshot.index("state.cognition = projection.cognition;")
        render_call = snapshot.index("renderIndividualPerspective();")
        render_cognition_state_call = snapshot.index("renderCognitionState(projection.cognition);")
        self.assertLess(cognition_assignment, render_call)
        self.assertLess(render_call, render_cognition_state_call)
```

Then add these new test methods to the same class:

```python
    def test_app_boot_uses_the_single_individual_dispatcher(self):
        app_js = read("app.js")
        self.assertIn("import { renderIndividualPerspective } from \"./render/individual.js\";", app_js)
        self.assertNotIn("import { renderOrganism } from \"./render/organism.js\";", app_js)
        self.assertIn("renderIndividualPerspective();", app_js)
        self.assertNotIn("renderOrganism();", app_js)

    def test_switch_view_uses_the_single_individual_dispatcher(self):
        controls_js = read("ui", "controls.js")
        self.assertIn("else renderIndividualPerspective();", controls_js)

    def test_advance_uses_the_single_individual_dispatcher_unconditionally(self):
        controls_js = read("ui", "controls.js")
        self.assertIn("renderTimeline(); renderInspector(); renderIndividualPerspective();", controls_js)
        self.assertNotIn('if (state.view === "individual") renderOrganism();', controls_js)

    def test_organism_belief_click_uses_the_single_individual_dispatcher(self):
        organism_js = read("render", "organism.js")
        self.assertIn("renderIndividualPerspective();", organism_js)
        self.assertIn('import { renderIndividualPerspective } from "./individual.js";', organism_js)

    def test_senses_click_uses_the_single_individual_dispatcher(self):
        senses_js = read("render", "senses.js")
        self.assertIn("renderIndividualPerspective();", senses_js)
        self.assertIn('import { renderIndividualPerspective } from "./individual.js";', senses_js)
        self.assertNotIn('import { renderOrganism } from "./organism.js";', senses_js)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: several FAIL — the code changes below haven't been made yet.

- [ ] **Step 3: Rewire `app.js`**

Edit `observatory/app.js`. Change the import line (currently `import { renderOrganism } from "./render/organism.js";`) to:

```js
import { renderIndividualPerspective } from "./render/individual.js";
```

Change the boot line (currently `renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderHistory(); renderProfiles();`) to:

```js
renderSenses(); renderIndividualPerspective(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderHistory(); renderProfiles();
```

- [ ] **Step 4: Rewire `ui/controls.js`**

Edit `observatory/ui/controls.js`. Change the import line (currently `import { renderOrganism } from "../render/organism.js";`) to:

```js
import { renderIndividualPerspective } from "../render/individual.js";
```

In `switchView()`, change the final line (currently `if (view === "population") { renderPopulation(); renderPopulationInspector(); } else renderOrganism();`) to:

```js
  if (view === "population") { renderPopulation(); renderPopulationInspector(); } else renderIndividualPerspective();
```

In `advance()`, change the last line (currently `renderTimeline(); renderInspector(); if (state.view === "individual") renderOrganism();`) to:

```js
  renderTimeline(); renderInspector(); renderIndividualPerspective();
```

- [ ] **Step 5: Rewire `projection/snapshot.js`**

Edit `observatory/projection/snapshot.js` line 168 — change `renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();` to:

```js
  renderSenses(); renderIndividualPerspective(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();
```

Update its import — change `import { renderOrganism } from "../render/organism.js";` to `import { renderIndividualPerspective } from "../render/individual.js";` (adjust the import position among the file's existing import block; keep the rest of the imports as they are).

- [ ] **Step 6: Rewire `transport/instance-stream.js`**

Edit `observatory/transport/instance-stream.js`. Change the import line (currently `import { renderOrganism } from "../render/organism.js";`) to:

```js
import { renderIndividualPerspective } from "../render/individual.js";
```

Also update the stale comment above `currentInstanceHasSnapshot`'s declaration — it currently reads (in part) `"...ingestSnapshot's own renderOrganism() call (inside..."`; change that phrase to `"...ingestSnapshot's own renderIndividualPerspective() call (inside..."` so the comment still names the function it's actually referring to after this task's rename.

Change line 39 (currently `if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();`) to:

```js
      if (currentInstanceHasSnapshot) renderIndividualPerspective();
```

- [ ] **Step 7: Rewire `render/organism.js`**

Edit `observatory/render/organism.js`. Add a new import after the existing `import { renderInspector } from "./inspector.js";` line:

```js
import { renderIndividualPerspective } from "./individual.js";
```

Change the belief-node click handler (line 158, currently
`node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderOrganism(); document.querySelector(".inspector").classList.add("open"); });`)
to:

```js
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderIndividualPerspective(); document.querySelector(".inspector").classList.add("open"); });
```

(This creates the `organism.js` ↔ `individual.js` import cycle described in the spec and this plan's Global Constraints — safe because `renderIndividualPerspective` is a hoisted function only ever invoked from this click handler, never at module-evaluation time.)

- [ ] **Step 8: Rewire `render/senses.js`**

Edit `observatory/render/senses.js`. Change the import line (currently `import { renderOrganism } from "./organism.js";`) to:

```js
import { renderIndividualPerspective } from "./individual.js";
```

Change the sense-row click handler (currently ending with `renderInspector();\n      renderOrganism();\n      document.querySelector(".inspector").classList.add("open");`) — replace the `renderOrganism();` line with:

```js
      renderIndividualPerspective();
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: PASS (all tests, including the corrected ones).

- [ ] **Step 10: Run the full observatory suite to check for regressions**

Run: `python3 -m pytest observatory/ -x -q`
Expected: all pass. Pay particular attention to `test_contract.py` — nothing in this task should have broken any of its existing bundle-text assertions, since `renderOrganism`/`renderIndividualPerspective` naming isn't checked there except by the new tests Tasks 3-5 added.

- [ ] **Step 11: Commit**

```bash
git add observatory/app.js observatory/ui/controls.js observatory/projection/snapshot.js observatory/transport/instance-stream.js observatory/render/organism.js observatory/render/senses.js observatory/test_state_flow.py
git commit -m "refactor(observatory): rewire all renderOrganism() call sites to renderIndividualPerspective()"
```

---

## Task 7: Toggle interactivity — `switchOrganismView`, `applyIndividualCanvasVisibility`

**Files:**
- Modify: `observatory/ui/controls.js`
- Modify: `observatory/app.js`
- Modify: `observatory/test_state_flow.py`

**Interfaces:**
- Consumes: `#organism-view-toggle`/`.organism-view-option`/`#self-panel` (Task 3), `state.organismView` (Task 2), `renderIndividualPerspective` (Task 5, already imported into `controls.js` by Task 6).
- Produces: `switchOrganismView(organismView)`, `applyIndividualCanvasVisibility()` — exported from nowhere else needed (both are used only within `controls.js` itself, via its own click-listener registration and `switchView()`).

- [ ] **Step 1: Write the failing tests**

Add to `observatory/test_state_flow.py`'s `StateFlowTests` class:

```python
    def test_apply_individual_canvas_visibility_called_from_switch_view_and_switch_organism_view(self):
        controls_js = read("ui", "controls.js")
        define_index = controls_js.index("function applyIndividualCanvasVisibility(")
        switch_organism_view_start = controls_js.index("function switchOrganismView(")
        switch_view_start = controls_js.index("function switchView(")
        switch_view_end = controls_js.index("\n}", switch_view_start)
        switch_view_body = controls_js[switch_view_start:switch_view_end]
        self.assertLess(define_index, switch_organism_view_start)
        self.assertLess(define_index, switch_view_start)
        self.assertIn("applyIndividualCanvasVisibility();", switch_view_body)

    def test_switch_organism_view_sets_state_before_applying_visibility(self):
        controls_js = read("ui", "controls.js")
        start = controls_js.index("function switchOrganismView(")
        end = controls_js.index("\n}", start)
        body = controls_js[start:end]
        set_index = body.index("state.organismView = organismView;")
        visibility_index = body.index("applyIndividualCanvasVisibility();")
        render_index = body.index("renderIndividualPerspective();")
        persist_index = body.index('localStorage.setItem("symbiont-observatory-organism-view"')
        self.assertLess(set_index, visibility_index)
        self.assertLess(visibility_index, render_index)
        self.assertLess(render_index, persist_index)

    def test_apply_individual_canvas_visibility_covers_all_four_elements(self):
        controls_js = read("ui", "controls.js")
        start = controls_js.index("function applyIndividualCanvasVisibility(")
        end = controls_js.index("\n}", start)
        body = controls_js[start:end]
        self.assertIn('document.querySelector("#organism-canvas")', body)
        self.assertIn('document.querySelector("#self-panel")', body)
        self.assertIn('document.querySelector("#organism-view-toggle")', body)
        self.assertIn('document.querySelector(".canvas-legend")', body)

    def test_organism_view_option_buttons_get_aria_pressed_updates(self):
        controls_js = read("ui", "controls.js")
        self.assertIn('b.setAttribute("aria-pressed", String(active));', controls_js)

    def test_app_restores_stored_organism_view_on_boot(self):
        app_js = read("app.js")
        self.assertIn('localStorage.getItem("symbiont-observatory-organism-view")', app_js)
        self.assertIn('["phenotype", "self"].includes(storedOrganismView)', app_js)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: several FAIL — `switchOrganismView`/`applyIndividualCanvasVisibility` don't exist yet.

- [ ] **Step 3: Add `applyIndividualCanvasVisibility` and `switchOrganismView` to `ui/controls.js`**

Insert these two functions immediately before the existing `switchView` function definition:

```js
function applyIndividualCanvasVisibility() {
  const isIndividual = state.view === "individual";
  const isPhenotype = isIndividual && state.organismView === "phenotype";
  document.querySelector("#organism-canvas").classList.toggle("hidden", !isPhenotype);
  document.querySelector("#self-panel").classList.toggle("hidden", !(isIndividual && state.organismView === "self"));
  document.querySelector("#organism-view-toggle").classList.toggle("hidden", !isIndividual);
  document.querySelector(".canvas-legend").classList.toggle("hidden", !isPhenotype);
}

function switchOrganismView(organismView) {
  state.organismView = organismView;
  document.querySelectorAll(".organism-view-option").forEach(b => {
    const active = b.dataset.organismView === organismView;
    b.classList.toggle("active", active);
    b.setAttribute("aria-pressed", String(active));
  });
  applyIndividualCanvasVisibility();
  renderIndividualPerspective();
  localStorage.setItem("symbiont-observatory-organism-view", organismView);
}
```

- [ ] **Step 4: Update `switchView` to use the new visibility helper**

In `switchView()`, replace the line
`document.querySelector("#organism-canvas").classList.toggle("hidden", view !== "individual");`
with:

```js
  applyIndividualCanvasVisibility();
```

(Leave the following line — `document.querySelector("#population-canvas").classList.toggle("hidden", view !== "population");` — unchanged; Population's own visibility isn't part of this helper.)

- [ ] **Step 5: Register the click listener for the new toggle buttons**

Add this line to `ui/controls.js`, near the existing `.toggle` listener registration (after the line `document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));`):

```js
document.querySelectorAll(".organism-view-option").forEach(button => button.addEventListener("click", () => switchOrganismView(button.dataset.organismView)));
```

- [ ] **Step 6: Restore the stored organism view on boot in `app.js`**

Add this after the existing `storedView` restore line in `app.js` (`const storedView = localStorage.getItem("symbiont-observatory-view"); if (["individual", "population"].includes(storedView)) switchView(storedView);`):

```js
const storedOrganismView = localStorage.getItem("symbiont-observatory-organism-view");
if (["phenotype", "self"].includes(storedOrganismView)) document.querySelector(`[data-organism-view="${storedOrganismView}"]`).click();
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest observatory/test_state_flow.py -v`
Expected: PASS (all tests).

- [ ] **Step 8: Run the full observatory suite**

Run: `python3 -m pytest observatory/ -x -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add observatory/ui/controls.js observatory/app.js observatory/test_state_flow.py
git commit -m "feat(observatory): wire Phenotype/Self toggle interactivity"
```

---

## Task 8: Full regression + manual Playwright verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the entire repository test suite**

Run: `cd /home/alessbarb/workspace/repos/incubating/symbiont-lab && python3 -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Serve Observatory and open it**

Run: `python3 -m http.server 8787 --directory observatory &` (or `nohup ... &` if the shell needs it to survive). Use the Playwright MCP tools: `browser_navigate` to `http://127.0.0.1:8787/`, then `browser_console_messages` with `level: "error"`.
Expected console errors: at most the two pre-existing/expected ones (`/fleet` 404, `favicon.ico` 404). Any error naming a `render/`, `projection/`, `ui/`, or `transport/` file path is a real regression — stop and fix before continuing.

- [ ] **Step 3: Walk the toggle behavior checklist**

Via `browser_snapshot`/`browser_click`/`browser_evaluate` (same pattern as PR2's Task 8 verification): click "Use demo" to dismiss the welcome overlay. Confirm the Phenotype/Self sub-toggle is visible in Individual view. Use `browser_evaluate` to check `document.querySelector("#organism-view-toggle").classList.contains("hidden")` is `false`, `#organism-canvas` is visible (not `.hidden`), `#self-panel` has `.hidden`, and `.canvas-legend` is visible. Click the "Self" button; re-check via `browser_evaluate`: `#organism-canvas` now `.hidden`, `#self-panel` no longer `.hidden` and contains the text "Body schema not yet developed", `.canvas-legend` now `.hidden`, and the "Self" button has `aria-pressed="true"` while "Phenotype" has `aria-pressed="false"`. Click a sense row in the sidebar while Self is active; confirm no console errors and `#self-panel`'s content is unchanged (same text, still present). Click back to "Phenotype"; confirm `#organism-canvas` is visible again and shows the same organism SVG PR2 produced (boundary + receptors + belief circles), `.canvas-legend` visible again. Switch to Population view; confirm `#organism-view-toggle` is now `.hidden`. Switch back to Individual; confirm the toggle reappears still showing "Phenotype" active (the last individual-view choice, not reset). Click "Self" again, then reload the page (`browser_navigate` to the same URL); confirm Self is still active after reload (via `localStorage` persistence) and the message still renders correctly.

- [ ] **Step 4: Clean up**

```bash
pkill -f "http.server 8787"
rm -rf .playwright-mcp
git status --short
```

Expected: working tree clean except for the commits already made in Tasks 1-7 (and any pre-existing unrelated uncommitted file noted by earlier PRs, which stays untouched) — no stray Playwright debug artifacts.

- [ ] **Step 5: Final confirmation**

No commit in this task (verification-only) — if Steps 1-3 all pass, PR3 is complete and matches the spec's exit condition (§31 Phase 3: "Observatory explicitly distinguishes scientific view from organism self-view").
