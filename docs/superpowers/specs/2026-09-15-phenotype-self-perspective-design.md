# Observatory PR3: Phenotype/Self perspective toggle

Status: approved by owner 2026-09-15; revised 2026-09-15 after owner
code review against the real codebase (see "Revision history" at the
end). Implements Phase 3 of
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
- No changes to `render/inspector.js`, `render/senses.js`'s own render
  logic, `render/population.js` — the senses sidebar, belief inspector,
  timeline, and Population view are untouched in what they show; the
  toggle only swaps the central canvas's content within the existing
  Individual view. (`render/senses.js` does get one call-site edit — see
  "The single Individual-perspective entrypoint" below — but its own
  rendering behavior is unchanged.)
- No synthesizing anything from `state.topology`/`state.cognition`/
  `state.senses`/`state.beliefs` for the Self view — Research Invariant
  I1 ("no false self-knowledge") is what this architectural seam exists
  to protect, and the cheapest way to violate it is to let the Self view
  quietly fall back to phenotype data when self data is missing. It must
  not do that, ever, including in PR3.

## Design

### The single Individual-perspective entrypoint

Before PR3, `renderOrganism()` is called directly from six places:
`app.js`'s boot sequence, `ui/controls.js`'s `switchView()` and
`advance()`, `projection/snapshot.js`'s `ingestSnapshot()`,
`transport/instance-stream.js`'s topology-message handler, and
`render/organism.js`'s own belief-node click handler and
`render/senses.js`'s sense-row click handler. If PR3 only taught
`switchView()`/`switchOrganismView()` about `state.organismView` and left
the other five call sites calling `renderOrganism()` directly, Self would
only ever repaint when the user clicks the toggle — every tick, every
snapshot, every belief/sense click would silently redraw the *hidden*
Phenotype SVG and leave Self's content stale. That's invisible in PR3
(Self's content is static text, so "stale" and "fresh" render identically),
but it means PR3 would not actually build the seam it exists to build:
PR5 needs Self to re-render on every incoming `bodySchema` change, and
retrofitting that later is exactly the kind of deferred architectural
debt worth avoiding now, while the fix is one function and six call-site
edits.

New file `render/individual.js`:

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

This is the **only** place that reads `state.organismView` to decide
what to draw. Principle, stated explicitly so it survives into PR4/PR5:
**no transport, projection, or UI module decides Phenotype vs. Self for
itself** — every call site that used to call `renderOrganism()` as its
top-level "repaint the individual view" action now calls
`renderIndividualPerspective()` instead, unconditionally (no
`if (state.view === "individual")` or `if (state.organismView === ...)`
guard duplicated at the call site — `renderIndividualPerspective()`
already contains both checks, once). The six call sites become:

1. `app.js` boot line — `renderOrganism()` → `renderIndividualPerspective()`.
2. `ui/controls.js`'s `switchView()` — its `else renderOrganism();` branch
   (already inside an `if (view === "population") {...} else {...}`, so
   `state.view === "individual"` is already established) →
   `else renderIndividualPerspective();`.
3. `ui/controls.js`'s `advance()` — its
   `if (state.view === "individual") renderOrganism();` line → drop the
   guard, just `renderIndividualPerspective();` (the function has its own
   guard now, so the call site's guard is redundant duplication of a
   decision that belongs in one place).
4. `projection/snapshot.js`'s `ingestSnapshot()` — its
   `renderSenses(); renderOrganism(); renderPopulation(...); ...` line →
   swap `renderOrganism()` for `renderIndividualPerspective()` in place.
5. `transport/instance-stream.js`'s topology handler — its
   `if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();`
   line → drop the `state.view === "individual"` half of the guard (now
   redundant with the function's own check) but **keep** the
   `currentInstanceHasSnapshot` half (that one is instance-stream's own
   race-condition concern from PR2, unrelated to Phenotype/Self and not
   this PR's to remove): `if (currentInstanceHasSnapshot) renderIndividualPerspective();`.
6. `render/organism.js`'s own belief-node click handler and
   `render/senses.js`'s sense-row click handler both currently call
   `renderOrganism()` after updating `state.selected` — both become
   `renderIndividualPerspective()` calls too, via a new import of
   `render/individual.js`, so that clicking a belief or sense while Self
   is active correctly leaves Self's content alone (calling `renderSelf()`
   again, which is a harmless idempotent redraw of static text) instead
   of needlessly repainting the hidden Phenotype SVG.

`render/organism.js`'s and `render/senses.js`'s new imports of
`render/individual.js`, combined with `render/individual.js`'s own import
of `render/organism.js`, form an import cycle
(`individual.js → organism.js → individual.js`, and separately
`individual.js → self.js`, with no cycle back from `self.js`). This is
safe under the same discipline PR1 already established for its
`render/timeline.js`↔`ui/controls.js`↔`projection/snapshot.js` cycle:
every function involved is a hoisted `function` declaration, none of them
are invoked at module-evaluation time (only later, from event handlers or
`setInterval`), so the cycle never observes an uninitialized binding.

### `state.organismView`

New field: `"phenotype" | "self"`, default `"phenotype"`. Added to
`state/demo-state.js`'s `createInitialState()` object literal (same
object PR2 already added `topology`/`cognition`/`instanceId` to), along
with `bodySchema: null` (see "`projection/self-schema.js`" below for why
this is `null` rather than simply absent). Persisted to `localStorage`
under `"symbiont-observatory-organism-view"`, restored on boot in
`app.js` — same pattern as the existing `"symbiont-observatory-profile"`
restore (`app.js:21`, a
`document.querySelector('[data-profile="..."]').click()` trick that
reuses the real click handler rather than duplicating its logic).

### Markup (`index.html`)

New sub-toggle inside `.canvas-wrap` (not the global `.view-toggle`
header nav at `index.html:14-17` — per design doc §24, "this toggle
belongs inside the individual view"), inserted as a sibling to the
existing `#population-tools` block (`index.html:43-45`):

```html
<div id="organism-view-toggle" class="organism-view-toggle" aria-label="Individual view perspective">
  <button class="organism-view-option active" data-organism-view="phenotype" aria-pressed="true">Phenotype</button>
  <button class="organism-view-option" data-organism-view="self" aria-pressed="false">Self</button>
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

### `.canvas-legend` visibility

`.canvas-legend` (`index.html:48-53`: Perception/Belief/Attention/
Contradiction) is currently a sibling of both canvases, always visible
regardless of `state.view`/`state.organismView` — including today, in
Population view, where it doesn't apply either (pre-existing minor
inconsistency). Left alone, the Self panel would show underneath a
legend describing Phenotype-only visual elements it has none of,
implying they're part of Self. `applyIndividualCanvasVisibility()`
(below) additionally toggles `.canvas-legend`'s `.hidden` class, visible
only when `state.view === "individual" && state.organismView === "phenotype"`
— which also fixes the pre-existing Population-view inconsistency as a
side effect, not a deliberate scope expansion.

### `projection/self-schema.js` (new, pure)

Named `projectSelfSchema`/`self-schema.js`, not `projectSelfModel`/
`self-model.js` — `SelfModel` is already a specific, real Python class
(`src/symbiont/core/selfmodel.py`) with a specific meaning (learned
per-sense cost/health/confidence/maturity/recency). This function
projects the *organism's exported self-schema* (the eventual
`BodySchema`, per the design doc's own naming in §9/§25), which in a
later PR will be built partly *from* `SelfModel` as one evidence source
among several — reusing `SelfModel`'s name here would collide with that
real, different thing and get more confusing exactly when PR4 introduces
`BodySchemaEngine` consuming `SelfModel` as input.

```js
function projectSelfSchema(bodySchema) {
  if (!bodySchema) {
    return { state: "undeveloped", parts: [], dependencies: [] };
  }
  // bodySchema's wire shape is not part of PR3's contract — PR3 never
  // passes anything but null/undefined here (state.bodySchema is always
  // null in this PR; there is no PR4 yet to ever set it otherwise). This
  // branch exists only so the function's signature is forward-shaped for
  // PR5, which will replace this body with real state/kind discrimination
  // once BodySchema's actual exported shape exists — it deliberately does
  // NOT infer "developed" from mere truthiness, since a truthy-but-empty
  // or malformed bodySchema is not evidence of a developed self-model.
  return { state: "undeveloped", parts: [], dependencies: [] };
}
export { projectSelfSchema };
```

Zero imports, pure — same discipline as `projection/morphology.js`/
`projection/topology.js`. Simple enough (no geometry, no PRNG) that it
doesn't strictly need the Node-subprocess harness for its own logic, but
since the harness already exists and the function is trivial to call
through it, PR3 uses it anyway for a real behavioral test (see Testing)
rather than only a textual one — cheap to do correctly, and this
function is exactly the epistemic boundary the whole PR exists to
protect, so it earns the extra rigor.

### `render/self.js` (new)

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

`projectSelfSchema(null)` — not `state.bodySchema` — deliberately: PR3
never reads `state.bodySchema` from `render/self.js` at all, even though
the field exists on `state` (see above), so that the function call
itself is legible proof this module touches no privileged state; PR5
changes this one call site to `projectSelfSchema(state.bodySchema)` when
`state.bodySchema` can actually vary. Tone matches the existing
`render/cognition.js` "no cognition data" precedent (`cognition.js:24-33`)
— a contextual, non-alarming explanation, not silence or an error state.
The added `scope` paragraph directly states the boundary from the design
doc §26 in user-facing language, making the phenotype/self split legible
to a human reading the page, not just to the code.

### `ui/controls.js` changes

New `switchOrganismView(organismView)`, and a small shared helper both it
and `switchView()` call, to avoid duplicating the two-dimensional
visibility logic in two places:

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

`switchView()` (existing, `controls.js:12-22`) gets its
`#organism-canvas`/`.hidden` line (currently
`document.querySelector("#organism-canvas").classList.toggle("hidden", view !== "individual");`)
replaced by a call to `applyIndividualCanvasVisibility()`, and its final
render dispatch (`if (view === "population") { renderPopulation(); renderPopulationInspector(); } else renderOrganism();`)
changed to `else renderIndividualPerspective();` per "The single
Individual-perspective entrypoint" above. A new listener registers the
click handler for `.organism-view-option` buttons, following the file's
existing pattern
(`document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));`
at `controls.js:35`).

### `app.js` changes

Swap the boot sequence's `renderOrganism()` call for
`renderIndividualPerspective()` (import from `render/individual.js`
instead of `render/organism.js` — nothing else in `app.js` needs
`renderOrganism` directly anymore). Add the `organismView` localStorage
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

`observatory/test_self_schema.py` (new, Node-subprocess, following
`test_topology.py`'s/`test_morphology.py`'s harness pattern): behavioral,
not textual —
- `projectSelfSchema(null)` and `projectSelfSchema(undefined)` both →
  `{state: "undeveloped", parts: [], dependencies: []}`.
- `projectSelfSchema({})` (a truthy-but-empty object, the case Finding 2
  of the review specifically flagged) → still `"undeveloped"`, not
  `"developed"` — this is the one behavioral assertion that would have
  caught the original draft's bug.
- `self-schema.js` has zero imports (read the file's source, assert no
  `import` keyword appears — same check style as PR2's zero-import
  constraint, just verified for this file too).

`observatory/test_contract.py`: new assertions — `#organism-view-toggle`/
`#self-panel` element ids present in `index.html`; `function
projectSelfSchema(` present in `self-schema.js`; `function renderSelf(`
present in `self.js`; `"Body schema not yet developed"` text present
somewhere in the bundle (the concrete, checkable form of the design
doc's required messaging). Additionally, a deliberate string-absence
check on `render/self.js` specifically (not the whole bundle, since
`state.topology` etc. legitimately appear elsewhere): none of
`"state.topology"`, `"state.cognition"`, `"state.senses"`,
`"state.beliefs"` may appear in `render/self.js`'s source. This is a
textual check standing in for a real architectural invariant ("Self
rendering must not consume privileged phenotype state") — not a
general endorsement of string-matching as architecture, but the right
tool for a rule this specific and this important to keep enforced as
the codebase grows.

`observatory/test_state_flow.py`: new assertions (textual/positional,
matching the file's existing convention) —
`applyIndividualCanvasVisibility` called from both `switchView` and
`switchOrganismView`; `switchOrganismView` sets `state.organismView`
before calling `applyIndividualCanvasVisibility()`; `renderIndividualPerspective`
(not `renderOrganism`) is what `app.js`'s boot sequence, `switchView`'s
individual branch, `advance()`, `ingestSnapshot()`, and
`instance-stream.js`'s topology handler each call — one assertion per
call site, so a future edit that reintroduces a direct `renderOrganism()`
call at any of those five sites fails a test instead of silently
reopening this PR's core bug.

## Verification

- `pytest observatory/ -x` green.
- Manual Playwright pass: serve `observatory/`, confirm zero new console
  errors; in Individual view, confirm the Phenotype/Self sub-toggle
  appears (with correct `aria-pressed` state) and Population view does
  not show it, and confirm `.canvas-legend` is hidden in both Population
  view and Self view, visible only in Phenotype; click Self, confirm
  `#organism-canvas` hides, `#self-panel` shows the "Body schema not yet
  developed" message plus the scope-clarifying sentence; while Self is
  active, click a sense row in the sidebar and confirm the central panel
  does not flash/replace with organism geometry (only `renderSelf()`'s
  harmless idempotent redraw happens); click back to Phenotype, confirm
  the organism SVG returns unchanged from PR2's behavior; switch to
  Population and back to Individual, confirm the last-selected
  Phenotype/Self choice is preserved (not reset to Phenotype); reload
  the page, confirm the choice survives via `localStorage`.
- Exit condition (§31 Phase 3): "Observatory explicitly distinguishes
  scientific view from organism self-view" — satisfied by the toggle
  existing, by `renderIndividualPerspective()` being the sole dispatch
  point (so the distinction is structurally enforced, not just true by
  coincidence of what currently happens to be static), and by the Self
  view never reading `state.topology`/`state.cognition`/`state.senses`/
  `state.beliefs` (enforced by the `test_contract.py` string-absence
  check above).

## Revision history

- 2026-09-15 initial version approved by owner.
- 2026-09-15 revised after owner code review against the real codebase.
  Verified and incorporated: `renderOrganism()` was called directly from
  six sites, not just the two toggle handlers — introduced
  `render/individual.js`'s `renderIndividualPerspective()` as the single
  dispatch point and rewired all six call sites, establishing the actual
  architectural seam PR5 needs rather than one that only looks complete
  while Self's content happens to be static; `projectSelfModel` renamed
  to `projectSelfSchema` (and the file to stay `self-schema.js`) to avoid
  colliding with the real, differently-scoped Python `SelfModel` class;
  fixed the function to never infer `"developed"` from mere truthiness of
  its input (a `{}` argument now correctly still yields `"undeveloped"`);
  added `state.bodySchema: null` explicitly rather than relying on
  `undefined`, so "no BodySchema yet" is a stated contract value, not an
  absent-field accident; `.canvas-legend` now hidden outside
  Phenotype-individual (also incidentally fixing its pre-existing
  always-visible-in-Population inconsistency); added the scope-clarifying
  sentence to the Self panel's message so the phenotype/self split is
  legible to a human reader, not just enforced in code; added
  `aria-pressed` to the toggle buttons; added a real Node-subprocess
  behavioral test for `projectSelfSchema` (including the `{}` case) and a
  targeted string-absence test on `render/self.js` for the four
  privileged-state identifiers.
