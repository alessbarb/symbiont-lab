# Observatory PR3: Phenotype/Self perspective toggle

Status: approved by owner 2026-09-15. Implements Phase 3 of
`docs/design/digital-body-schema-and-emergent-morphology.md` (§17-18,
§24-26, §31 Phase 3), the third PR of that doc's 6-PR sequence (§36).
Builds on PR1 (module split) and PR2 (deterministic phenotype
morphology), both already merged to `main`.

## Problem

The design doc's core distinction — "what the organism *is*" (Phenotype,
scientific view) vs. "what the organism *believes it is*" (Self,
organism-owned view) — has no architectural seam in Observatory yet.
There is one Individual/Population toggle and one canvas; there is no
way to ask Observatory to show only what the organism itself reports
about itself, as opposed to everything the apparatus can observe.

## Investigation finding (binds scope)

The design doc's §2 states "the current organism already maintains a
limited `SelfModel`" implying Self-view data already exists somewhere
reachable. Verified against the actual code: `SelfModel` does exist
(`src/symbiont/core/selfmodel.py`, exporting per-sense `cost_class`/
`health_class`/`confidence_class`/`maturity_class`/`recency_class` via
`SelfModel.export()`), but it is **not wired to Observatory anywhere** —
not in `adapter.py`, not in any `observatory/*.schema.json`, not in
`state/demo-state.js`. It is currently written only into the organism's
own durable checkpoint (`runtime.py:409`).

Owner decision 2026-09-15: PR3 stays Observatory-UI-only. It builds the
toggle architecture and the `undeveloped`/`partial`/`developed` self-schema
contract the design doc specifies (§25), with the contract permanently
returning `undeveloped` for now, since nothing is exported yet. Wiring
`SelfModel`/`BodySchema` export through `adapter.py` into a schema and
`state` is explicitly PR4/PR5 territory (design doc §36), not this PR.
Zero Python/backend changes in this PR.

## Non-goals

- No `adapter.py`, schema, or backend changes of any kind.
- No changes to `render/inspector.js`, `render/senses.js`,
  `render/population.js` — the senses sidebar, belief inspector, timeline,
  and Population view are untouched; the toggle only swaps the central
  canvas's content within the existing Individual view.
- No synthesizing anything from `state.topology`/`state.cognition` for
  the Self view — Research Invariant I1 ("no false self-knowledge") is
  what this architectural seam exists to protect, and the cheapest way to
  violate it is to let the Self view quietly fall back to phenotype data
  when self data is missing. It must not do that, ever, including in PR3.

## Design

### `state.organismView`

New field: `"phenotype" | "self"`, default `"phenotype"`. Added to
`state/demo-state.js`'s `createInitialState()` object literal (same
object PR2 already added `topology`/`cognition`/`instanceId` to).
Persisted to `localStorage` under `"symbiont-observatory-organism-view"`,
restored on boot in `app.js` — same pattern as the existing
`"symbiont-observatory-profile"` restore (`app.js:21`, a
`document.querySelector('[data-profile="..."]').click()` trick that
reuses the real click handler rather than duplicating its logic).

### Markup (`index.html`)

New sub-toggle inside `.canvas-wrap` (not the global `.view-toggle`
header nav at `index.html:14-17` — per design doc §24, "this toggle
belongs inside the individual view"), inserted as a sibling to the
existing `#population-tools` block (`index.html:43-45`):

```html
<div id="organism-view-toggle" class="organism-view-toggle" aria-label="Individual view perspective">
  <button class="organism-view-option active" data-organism-view="phenotype">Phenotype</button>
  <button class="organism-view-option" data-organism-view="self">Self</button>
</div>
```

New `#self-panel` sibling to `#organism-canvas`/`#population-canvas`
(`index.html:46-47`) — a plain `<div>`, not `<svg>`, since an
`undeveloped` self-schema has no geometry to draw:

```html
<div id="self-panel" class="self-panel hidden"></div>
```

`#organism-view-toggle` and `#population-tools` occupy the same visual
slot (top-center overlay on the canvas) and are never shown
simultaneously (one requires `view === "individual"`, the other
`view === "population"`), so `#organism-view-toggle` reuses
`.population-tools`'s existing position/z-index CSS pattern under its
own class name — no layout collision to design around.

### `projection/self-schema.js` (new, pure)

```js
function projectSelfModel(bodySchema) {
  if (!bodySchema) {
    return { state: "undeveloped", parts: [], dependencies: [] };
  }
  return { state: "developed", parts: bodySchema.parts ?? [], dependencies: bodySchema.dependencies ?? [] };
}
export { projectSelfModel };
```

Zero imports, pure — same discipline as `projection/morphology.js`/
`projection/topology.js`, but trivial enough (no geometry, no PRNG) that
it doesn't need the Node-subprocess test harness; the repo's lighter
textual-assertion convention (as used in `test_state_flow.py`) is
proportionate here. `state.bodySchema` doesn't exist on `state` in PR3
(there is nothing that would ever set it — no PR4 yet) — every call in
PR3 is `projectSelfModel(undefined)`, always returning the `undeveloped`
shape. The `"partial"` state from the design doc's three-state contract
(§25) has no trigger condition yet in PR3 and is intentionally
unreachable code in this PR — the function signature accepts it
structurally (any future `bodySchema.state === "partial"` would need a
future PR to actually produce), but PR3 never exercises it. This is
correct forward-compatibility, not dead code to prune: PR5 is the PR
that will make `"partial"`/`"developed"` reachable, and changing this
function's shape then, instead of now, is exactly the kind of
future-PR churn worth avoiding by getting the contract right once.

### `render/self.js` (new)

```js
function renderSelf() {
  const panel = document.querySelector("#self-panel");
  const projection = projectSelfModel(state.bodySchema);
  panel.replaceChildren();
  const heading = document.createElement("h2");
  const body = document.createElement("p");
  if (projection.state === "undeveloped") {
    heading.textContent = "Body schema not yet developed";
    body.textContent = "This organism does not yet export a model of its own body. Once available, this view will show only what the organism itself believes about its parts and their relationships — never reconstructed from what Observatory can otherwise observe.";
  }
  panel.append(heading, body);
}
export { renderSelf };
```

Tone matches the existing `render/cognition.js` "no cognition data"
precedent (`cognition.js:24-33`) — a contextual, non-alarming explanation,
not silence or an error state. `state`/`document` come from the same
imports every other render module already uses
(`import { state } from "../state/store.js";`).

### `ui/controls.js` changes

New `switchOrganismView(organismView)`, and a small shared helper both it
and `switchView()` call, to avoid duplicating the two-dimensional
visibility logic in two places:

```js
function applyIndividualCanvasVisibility() {
  const isIndividual = state.view === "individual";
  document.querySelector("#organism-canvas").classList.toggle("hidden", !(isIndividual && state.organismView === "phenotype"));
  document.querySelector("#self-panel").classList.toggle("hidden", !(isIndividual && state.organismView === "self"));
  document.querySelector("#organism-view-toggle").classList.toggle("hidden", !isIndividual);
}

function switchOrganismView(organismView) {
  state.organismView = organismView;
  document.querySelectorAll(".organism-view-option").forEach(b => b.classList.toggle("active", b.dataset.organismView === organismView));
  applyIndividualCanvasVisibility();
  if (state.view === "individual") { if (organismView === "self") renderSelf(); else renderOrganism(); }
  localStorage.setItem("symbiont-observatory-organism-view", organismView);
}
```

`switchView()` (existing, `controls.js:12-22`) gets its two
`#organism-canvas`/`.hidden` lines (currently
`document.querySelector("#organism-canvas").classList.toggle("hidden", view !== "individual");`)
replaced by a call to `applyIndividualCanvasVisibility()`, and its final
render dispatch (`if (view === "population") {...} else renderOrganism();`)
changed to respect `state.organismView` on the individual branch:
`else if (state.organismView === "self") renderSelf(); else renderOrganism();`.
A new listener registers the click handler for `.organism-view-option`
buttons, following the file's existing pattern
(`document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));`
at `controls.js:35`).

### `app.js` changes

Import `renderSelf` (unconditionally called once at boot alongside the
existing `renderOrganism()` boot call, matching how `renderOrganism()`
itself is already called unconditionally at boot before any view
restoration runs — harmless, cheap, and keeps `#self-panel` non-empty
even before any toggle interaction). Add the `organismView` localStorage
restore line, mirroring the existing `storedProfile` pattern
(`app.js:21`):
```js
const storedOrganismView = localStorage.getItem("symbiont-observatory-organism-view");
if (["phenotype", "self"].includes(storedOrganismView)) document.querySelector(`[data-organism-view="${storedOrganismView}"]`).click();
```

### `styles.css` changes

New `.organism-view-toggle`/`.organism-view-option`/
`.organism-view-option.active` rules, visually matching the existing
`.population-tools`/`.population-mode`/`.population-mode.active` pattern
(`styles.css:84`) — same top-center overlay position, same border/
padding/border-radius idiom, distinct color accent (reuse `var(--cyan)`
to visually tie it to the Individual-view family, as opposed to
`.population-mode.active`'s mint). New `.self-panel` rule: fills the
canvas area the same way `#organism-canvas, #population-canvas` do
(`styles.css:85`), with padding and typography sized like the existing
`.canvas-heading`/`.panel-heading` text treatment (reuse those existing
class conventions rather than inventing new ones) so the "not yet
developed" message reads as an intentional page state, not a broken
layout.

## Testing

`observatory/test_contract.py`: new assertions —
`#organism-view-toggle`/`#self-panel` element ids present in
`index.html`; `function projectSelfModel(` present in
`self-schema.js`; `function renderSelf(` present in `self.js`;
`"Body schema not yet developed"` text present somewhere in the bundle
(the concrete, checkable form of the design doc's required messaging).

`observatory/test_state_flow.py`: new assertions (textual/positional,
matching the file's existing convention) — `applyIndividualCanvasVisibility`
called from both `switchView` and `switchOrganismView`;
`switchOrganismView` sets `state.organismView` before calling
`applyIndividualCanvasVisibility()`; the render dispatch inside
`switchView`'s individual branch checks `state.organismView === "self"`.

## Verification

- `pytest observatory/ -x` green.
- Manual Playwright pass: serve `observatory/`, confirm zero new console
  errors; in Individual view, confirm the Phenotype/Self sub-toggle
  appears and Population view does not show it; click Self, confirm
  `#organism-canvas` hides, `#self-panel` shows the "Body schema not yet
  developed" message, and the message persists across a demo tick
  (doesn't get silently replaced by organism geometry); click back to
  Phenotype, confirm the organism SVG returns unchanged from PR2's
  behavior; switch to Population and back to Individual, confirm the
  last-selected Phenotype/Self choice is preserved (not reset to
  Phenotype); reload the page, confirm the choice survives via
  `localStorage`.
- Exit condition (§31 Phase 3): "Observatory explicitly distinguishes
  scientific view from organism self-view" — satisfied by the toggle
  existing and the Self view never reconstructing anything from
  phenotype-only data (`state.topology`, `state.cognition`,
  `state.senses`, `state.beliefs` are never read by `self-schema.js` or
  `render/self.js`).
