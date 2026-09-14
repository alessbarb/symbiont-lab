# Digital Body Schema & Emergent Morphology

## Status

Proposed design.

This document defines the architecture for giving Symbiont a substrate-native form of self-perception and replacing Observatory's fixed cell metaphor with an emergent digital morphology.

The design deliberately separates three different things:

1. **the organism as it actually exists**;
2. **the organism's learned representation of itself**;
3. **the human-facing visualization produced by Observatory**.

These must never be silently collapsed into the same representation.

---

# 1. Motivation

Observatory currently represents an individual Symbiont using a fixed SVG cell-like outline.

That shape is a visualization metaphor chosen by the interface. It is not produced by the organism and does not represent anything Symbiont knows about itself.

The current organism already maintains a limited `SelfModel`, but that model describes only properties of its sensory apparatus such as:

* health,
* confidence,
* cost,
* maturity,
* recency.

It does not yet contain an explicit concept of:

* organism identity,
* body boundary,
* internal parts,
* functional dependencies,
* cognitive regions,
* global viability,
* organism continuity.

The next step is therefore not to decide whether Symbiont is a cell, sphere, graph or blob.

The next step is to introduce a **Digital Body Schema**.

The central idea is:

> A Symbiont has no intrinsic Euclidean shape. It has an organization.

Observatory may translate that organization into geometry, but the geometry is a projection.

---

# 2. Core distinction

The architecture defines three epistemic layers.

```text
ACTUAL ORGANISM
    │
    │ observable state
    ▼
PHENOTYPE PROJECTION
    │
    │ human visualization
    ▼
OBSERVATORY
```

and independently:

```text
ACTUAL ORGANISM
    │
    │ internal evidence
    ▼
BODY SCHEMA LEARNING
    │
    ▼
SELF MODEL
    │
    │ exported representation
    ▼
OBSERVATORY SELF VIEW
```

The Observatory therefore exposes two distinct views:

```text
[ Phenotype ] [ Self ]
```

## Phenotype View

Represents what the scientific apparatus can legitimately observe about the organism.

It may use:

* genome identity,
* current cognitive topology,
* sensory development,
* memory state,
* safety state,
* runtime state,
* health summaries,
* topology revision.

It is the external scientific view.

## Self View

Represents only what the organism currently knows or believes about itself.

It must use only the organism's exported self-representation.

Observatory must not fill missing knowledge using privileged runtime information.

This creates a meaningful distinction between:

```text
what I am
```

and:

```text
what I think I am
```

---

# 3. Design principle: no perfect introspection

The Body Schema must not simply expose the runtime's internal structures to cognition.

This would be invalid:

```python
body_schema.parts = cognitive_graph.nodes
body_schema.dependencies = cognitive_graph.edges
```

because it gives the organism perfect administrative introspection.

Instead, self-perception must be evidence-based.

```text
experience
   │
   ▼
evidence about own functioning
   │
   ▼
self hypotheses
   │
   ▼
consolidation
   │
   ▼
BodySchema
```

The organism should be able to be:

* incomplete about itself,
* uncertain about itself,
* temporarily wrong about itself,
* more knowledgeable about some regions than others.

That is not a defect.

It is part of the research model.

---

# 4. Digital body

A digital body is defined as the bounded organization whose continued operation constitutes the individual Symbiont.

It is not identical to the host computer.

It is not identical to the operating-system process.

It is not identical to the checkpoint.

Conceptually:

```text
HOST
  │
  ▼
computational substrate

RUNTIME
  │
  ▼
execution of organism

ORGANISM
  │
  ▼
persistent developmental individual

BODY SCHEMA
  │
  ▼
organism's representation of itself
```

The body boundary is therefore functional rather than geometric.

---

# 5. Initial body domains

The Body Schema is divided into five domains.

## 5.1 Identity

Represents continuity of the individual.

```text
identity
├── organism_id
├── genome_id
├── lineage_id
├── developmental_age_class
└── continuity_state
```

The organism does not need access to implementation-specific identifiers unless they form part of its explicit identity model.

---

## 5.2 Boundary

Represents the organism's current distinction between self and environment.

```text
boundary
├── known_self
├── known_environment
├── uncertain
└── future: other_organism
```

Membership should be learned or derived from bounded evidence.

Possible states:

```text
SELF
NON_SELF
UNCERTAIN
```

Future ecology adds:

```text
OTHER_SELF
```

---

## 5.3 Parts

A body part is a stable functional component represented by the organism.

Initial kinds:

```text
SENSE
COGNITIVE_REGION
MEMORY_REGION
READOUT_REGION
```

Future physiology may add:

```text
METABOLIC_REGION
MAINTENANCE_REGION
REPRODUCTIVE_REGION
```

Suggested internal model:

```python
@dataclass(slots=True)
class BodyPartState:
    part_id: str
    kind: BodyPartKind
    existence_confidence: float
    health: float
    functional_importance: float
    activity_class: ActivityClass
    recency_class: RecencyClass
    uncertainty: float
```

No geometry is stored.

Geometry belongs to Observatory.

---

# 6. Functional dependencies

A list of parts is not enough to form a body schema.

The organism must gradually learn relationships such as:

```text
part A contributes to part B
part C degrades when part D fails
part E is usually active before part F
part G supports organism viability
```

The self-model therefore includes bounded dependencies.

```python
@dataclass(slots=True)
class BodyDependency:
    source_id: str
    target_id: str
    relation: DependencyKind
    confidence_class: int
    support_class: int
```

Initial relation kinds should remain intentionally weak:

```text
SUPPORTS
CO_ACTS_WITH
PRECEDES
DEGRADES_WITH
UNKNOWN_DEPENDENCE
```

Avoid prematurely encoding causal semantics.

---

# 7. Global organism state

The schema also represents organism-level internal state.

Initial fields:

```text
global_state
├── self_model_confidence
├── integrity
├── stress
├── maintenance_load
├── dormancy_pressure
└── viability
```

Future physiology can add:

```text
metabolic_balance
resource_deficit
waste_pressure
repair_pressure
reproductive_readiness
```

These values should be:

* bounded,
* coarse,
* learned or computed from permitted internal evidence,
* checkpoint-safe,
* non-identifying.

---

# 8. Relationship with current SelfModel

The existing `SelfModel` should not be deleted.

It becomes one evidence source feeding the broader Body Schema.

```text
SelfModel
   │
   │ sensory health / cost / confidence
   ▼
BodySchemaEngine
```

The responsibilities remain distinct:

```text
SelfModel
→ how individual senses are doing

BodySchema
→ what parts of myself I believe exist and how they relate
```

This prevents a large, monolithic self-model.

---

# 9. BodySchemaEngine

Introduce:

```text
src/symbiont/core/body_schema.py
```

Suggested architecture:

```text
AdaptiveSenseModel ───────┐
SelfModel ────────────────┤
CognitiveBridge ──────────┤
MemoryConsolidator ───────┤
Runtime outcomes ─────────┤
SafetyState ──────────────┤
                           ▼
                    BodySchemaEngine
                           │
                           ▼
                       BodySchema
```

The engine receives bounded observations about the organism.

It must not receive arbitrary references to runtime internals.

---

# 10. First learning scope

The first implementation should be intentionally narrow.

## Phase A — Sensory body

The organism may learn:

```text
these senses belong to me
this sense is reliable
this sense is unhealthy
this sense is costly
this sense appears persistent
```

This can be built almost entirely from the existing `SelfModel`.

## Phase B — Cognitive regions

The organism begins learning coarse internal regions.

It should not be told:

```text
concept_0000000000000003
```

Instead, stable topology may be grouped into opaque regions:

```text
region.01
region.02
region.03
```

Region identity must remain persistent enough for longitudinal learning.

## Phase C — Dependencies

The organism learns that internal regions appear functionally related.

## Phase D — Global integrity

The organism forms a coarse model of:

```text
healthy
strained
unstable
recovering
dormant
```

---

# 11. Checkpoint representation

The Body Schema is persistent learned state.

Suggested checkpoint namespace:

```json
{
  "body_schema": {
    "schema_version": 1,
    "identity": {},
    "parts": [],
    "dependencies": [],
    "global_state": {}
  }
}
```

Requirements:

* bounded number of parts,
* bounded number of dependencies,
* quantized values,
* no raw activation history,
* no exact host readings,
* no runtime object names unless intentionally exposed,
* no implementation paths,
* no arbitrary strings originating from host resources.

---

# 12. Observatory projection architecture

Observatory must never directly convert `BodySchema` into internal cognition.

Its role remains passive.

The new individual visualization becomes:

```text
                 Observable organism state
                          │
                          ▼
                 MorphologyProjection
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
          Phenotype View         Self View
```

The projection is visual only.

It is not persisted back into Symbiont.

---

# 13. Emergent morphology

The current fixed cell boundary is replaced by a deterministic morphology generator.

No `cellPath` constant should remain.

Suggested input:

```typescript
interface PhenotypeMorphologyInput {
  identitySeed: string
  senseCount: number
  conceptCount: number
  readoutCount: number
  edgeCount: number
  topologyRevision: number
  health: number | null
  confidence: number | null
  frozen: boolean
}
```

The output remains geometry:

```typescript
interface MorphologyGeometry {
  boundaryPath: string
  senseAnchors: Point[]
  internalAnchors: Point[]
  coreAnchor: Point
}
```

---

# 14. Stable morphology identity

The organism should not change visual identity on every frame.

The basal contour must derive from a stable seed.

Preferred order:

```text
genome hash
+
organism identity
```

The genome defines inherited morphology characteristics.

The organism identity prevents genetically identical siblings from becoming visually indistinguishable.

Conceptually:

```text
genome
  │
  ├── inherited base morphology
  │
organism identity
  │
  └── individual variation
            │
            ▼
     stable basal shape
```

Developmental state produces small changes around that baseline.

---

# 15. Morphology semantics

Possible projection mapping:

| Organism property    | Visual representation         |
| -------------------- | ----------------------------- |
| Genome / identity    | stable base contour           |
| Sense                | peripheral receptor           |
| Active sense         | open / luminous receptor      |
| Probing sense        | intermittent receptor         |
| Dormant sense        | contracted receptor           |
| Concept              | internal region               |
| Readout              | integrative core              |
| Cognitive edge       | internal fibre                |
| Edge weight          | fibre intensity               |
| Health               | boundary integrity            |
| Confidence           | visual clarity                |
| Stress               | contour tension / contraction |
| Frozen state         | reduced motion / desaturation |
| Topology change      | slow structural rearrangement |
| Memory consolidation | persistent internal texture   |
| Pruning              | gradual disappearance         |
| New structure        | controlled growth             |

No biological organ names should be used in the data model.

---

# 16. Phenotype View

This view is allowed to display the actual observable phenotype.

Example for the historical worker-3 checkpoint:

```text
Phenotype

58 SENSE
5 CONCEPT
1 READOUT
0 EDGES
topology revision 29
```

The resulting morphology should visibly show:

* many peripheral receptors,
* five disconnected internal regions,
* a central readout region,
* no fabricated connectivity.

A graph with zero edges must look disconnected.

The visualization must never invent structure for aesthetics.

---

# 17. Self View

The Self View must be driven exclusively by:

```text
body_schema
```

During the transition period, before `BodySchema` exists, it may use only the current exported `SelfModel`.

It should explicitly indicate:

```text
BODY SCHEMA
not yet developed
```

rather than reconstructing the missing schema from topology.

This is especially important for organisms such as worker-3, where actual graph structure and self-modelled sensory state diverge.

---

# 18. Self/Phenotype divergence

Observatory should eventually distinguish four cases:

```text
REAL + KNOWN
REAL + UNKNOWN
BELIEVED + UNCONFIRMED
BELIEVED + CONTRADICTED
```

Suggested visual language:

```text
solid          = known
faint          = real but not self-modelled
dashed         = uncertain
fragmented     = contradicted
```

This is one of the scientifically valuable outputs of the design.

---

# 19. Refactoring Observatory

The current `observatory/app.js` has accumulated too many responsibilities.

Before implementing the complete Body Schema visualization, it should be decomposed.

Current responsibilities include:

* demo state,
* application state,
* SVG helpers,
* senses rendering,
* organism rendering,
* population rendering,
* inspector,
* timeline,
* replay,
* snapshot normalization,
* snapshot bounds checking,
* cognition rendering,
* SSE fleet connection,
* event history,
* UI actions.

This makes morphological evolution risky.

The refactor should happen as part of this work, not afterwards.

---

# 20. Proposed Observatory structure

```text
observatory/
│
├── app.js
│
├── state/
│   ├── store.js
│   ├── demo-state.js
│   └── selectors.js
│
├── transport/
│   ├── fleet-stream.js
│   ├── instance-stream.js
│   └── replay.js
│
├── projection/
│   ├── snapshot.js
│   ├── cognition.js
│   ├── morphology.js
│   └── self-schema.js
│
├── render/
│   ├── svg.js
│   ├── organism.js
│   ├── phenotype.js
│   ├── self.js
│   ├── senses.js
│   ├── population.js
│   ├── inspector.js
│   ├── timeline.js
│   └── cognition.js
│
├── ui/
│   ├── controls.js
│   ├── profiles.js
│   ├── drawers.js
│   └── dialogs.js
│
└── ...
```

`app.js` becomes composition only.

---

# 21. Target app.js

After refactor, `app.js` should be approximately orchestration code:

```javascript
import { createStore } from "./state/store.js";
import { createDemoState } from "./state/demo-state.js";
import { connectFleet } from "./transport/fleet-stream.js";
import { bindControls } from "./ui/controls.js";
import { renderApp } from "./render/app.js";

const store = createStore(createDemoState());

store.subscribe(state => {
  renderApp(state);
});

bindControls(store);
connectFleet(store);
```

The goal is not a specific line count.

The goal is that `app.js` no longer contains domain logic.

---

# 22. Pure morphology module

Create:

```text
observatory/projection/morphology.js
```

It must be deterministic and side-effect free.

Example API:

```javascript
export function projectPhenotypeMorphology(input) {
  return {
    boundary,
    receptors,
    regions,
    core,
  };
}
```

Tests must verify:

```text
same input → same morphology
same identity → stable base morphology
topology revision change → bounded shape evolution
frozen state → no structural invention
0 edges → no rendered fibres
```

---

# 23. Separate rendering from projection

Do not calculate organism structure inside SVG rendering code.

Bad:

```javascript
function renderOrganism() {
  // infer biology
  // create geometry
  // inspect cognition
  // manipulate DOM
}
```

Preferred:

```text
raw state
   │
   ▼
projection
   │
   ▼
geometry model
   │
   ▼
renderer
```

Example:

```javascript
const model = projectPhenotype(state);
renderPhenotype(canvas, model);
```

The renderer receives already-resolved semantics.

---

# 24. New morphology mode state

Add:

```javascript
state.organismView = "phenotype";
```

Allowed values:

```text
phenotype
self
```

UI:

```html
<div class="organism-view-toggle">
  <button data-organism-view="phenotype">Phenotype</button>
  <button data-organism-view="self">Self</button>
</div>
```

This toggle belongs inside the individual view, not in the global `Individual / Population` selector.

Hierarchy:

```text
Individual
    ├── Phenotype
    └── Self

Population
```

---

# 25. Observatory self projection

Create:

```text
observatory/projection/self-schema.js
```

It receives only exported self-model data.

No topology fallback.

Example:

```javascript
export function projectSelfMorphology(bodySchema) {
  if (!bodySchema) {
    return {
      state: "undeveloped",
      parts: [],
      dependencies: [],
    };
  }
}
```

The renderer must explicitly support:

```text
undeveloped
partial
developed
```

---

# 26. Topology source

The Phenotype view may use Observatory topology data.

The Self view must not.

This distinction must be tested.

Example invariant:

```text
topology.nodes = 64
body_schema.parts = 12

Phenotype view → may show 64 structural elements
Self view      → may show only 12 represented parts
```

No implicit merge.

---

# 27. SVG vocabulary cleanup

Rename existing cell-specific concepts.

```text
cellPath
→ phenotypeBoundary

cell-fill
→ organism-fill

membrane
→ phenotype-boundary

membrane-inner
→ phenotype-boundary-inner
```

The word `membrane` should only remain if used explicitly as a visual metaphor, not as a domain concept.

---

# 28. Accessibility

The visual distinction must have a textual equivalent.

Accessible table should eventually include:

```text
Perspective
Part
Type
Known to organism?
Confidence
Health
Relation
```

Example:

```text
Phenotype | sense_123 | sense | no | — | healthy
Self      | part.07   | sense | yes | high | healthy
```

Color must not be the only carrier of meaning.

---

# 29. Observatory schema evolution

The snapshot contract should eventually add an optional self-model section.

Possible v3:

```json
{
  "schema_version": 3,
  "organism": {
    "cognition": {},
    "self": {
      "body_schema": {}
    }
  }
}
```

Do not force this into v2 if doing so weakens version semantics.

Preferred rule:

```text
v1 → no cognition
v2 → cognition
v3 → cognition + optional/required body schema according to contract
```

The exact compatibility rule should be made explicit in JSON Schema.

---

# 30. Research invariants

The implementation must preserve the following invariants.

## I1 — No false self-knowledge

Observatory must never synthesize body-schema knowledge from privileged topology.

## I2 — Visualization is one-way

Morphology never feeds back into cognition.

## I3 — Stable identity

The same organism should not appear as a completely different morphology between adjacent ticks without a corresponding developmental event.

## I4 — Developmental change is bounded

Morphological change must reflect real state changes and remain temporally smooth.

## I5 — No fabricated connectivity

If the graph has zero edges, no apparent cognitive connections are drawn.

## I6 — Self can be incomplete

Missing BodySchema data is valid.

## I7 — Self can disagree with phenotype

Divergence is preserved rather than corrected by the Observatory.

## I8 — Human geometry is not organism knowledge

SVG coordinates are never exposed back to Symbiont.

---

# 31. Development phases

## Phase 1 — Observatory refactor

No behavioral change.

Tasks:

* split `app.js`,
* isolate store,
* isolate snapshot projection,
* isolate SVG helpers,
* isolate render modules,
* maintain existing UI behavior,
* preserve replay/SSE semantics.

Exit condition:

> Observatory behaves identically to the current version with the old visual model, but rendering and projection are modular.

---

## Phase 2 — Phenotype morphology

Replace fixed cell.

Tasks:

* deterministic morphology seed,
* generated phenotype boundary,
* peripheral sensory layout,
* internal concept/readout layout,
* topology-derived fibres,
* health/safety visual modulation.

Exit condition:

> Two organisms with different phenotype/identity can visibly differ without invented structure.

---

## Phase 3 — Individual perspective toggle

Introduce:

```text
Phenotype | Self
```

Self initially displays:

```text
Body schema not yet developed
```

where no body schema is exported.

Exit condition:

> Observatory explicitly distinguishes scientific view from organism self-view.

---

## Phase 4 — Sensory BodySchema

Implement in organism:

```text
src/symbiont/core/body_schema.py
```

Initial scope:

* sensory parts only,
* membership,
* health,
* confidence,
* recency,
* global schema confidence.

Exit condition:

> The organism can represent a subset of its own sensory apparatus without being handed the complete runtime topology.

---

## Phase 5 — Cognitive regions

Introduce coarse learned internal regions.

Exit condition:

> Symbiont can represent internal cognitive organization using opaque region identities.

---

## Phase 6 — Functional dependencies

Add learned relationships between body parts.

Exit condition:

> Self View can show organism-inferred internal structure rather than only parts.

---

## Phase 7 — Physiology integration

Connect BodySchema to Milestone F.

Add:

* stress,
* maintenance,
* dormancy,
* viability,
* metabolic state.

At this point the Body Schema becomes the organism's functional digital body model.

---

# 32. Testing strategy

## Unit tests

### Morphology

```text
same seed = same boundary
different identity = distinguishable boundary
health does not change identity
edge count controls fibres
no edge means no fibre
```

### BodySchema

```text
bounded parts
bounded dependencies
unknown part remains unknown
self membership does not come from evaluator
confidence evolves with evidence
checkpoint round-trip preserves consolidated schema
```

## Contract tests

Validate:

```text
v1
v2
v3
```

and reject illegal cross-version combinations.

## Integration tests

Example protocol:

```text
organism develops senses
→ SelfModel stabilizes
→ BodySchema discovers sensory parts
→ Observatory receives body_schema
→ Self View renders only known parts
```

## Adversarial tests

Ensure Observatory cannot:

```text
read phenotype topology
and silently insert it into Self View
```

---

# 33. Worker-3 validation protocol

Use the existing worker-3 checkpoint as the first reference case.

Expected phenotype:

```text
58 senses
5 concepts
1 readout
0 edges
```

Expected initial self view:

```text
partial sensory self-model
no complete cognitive body schema
```

The visualization should therefore show a visible mismatch.

This becomes a regression fixture for the core principle:

> Phenotype truth and self-perception are not the same data source.

---

# 34. Future extensions

The design intentionally supports later milestones.

## Digital physiology

Body Schema can represent:

```text
metabolism
maintenance
stress
waste pressure
viability
```

## Reproduction

Body Schema can later represent:

```text
lineage
reproductive maturity
offspring relation
continuity before/after fission
```

## Ecology

The boundary model gains:

```text
SELF
ENVIRONMENT
OTHER_SELF
```

This enables studying whether Symbiont distinguishes:

```text
me
world
other organism
```

without hand-coding social identity directly into cognition.

---

# 35. Long-term research question

The final objective is not to create a prettier visualization.

The objective is to make this measurable:

```text
actual organism
       │
       ├───────────────┐
       ▼               ▼
what it is       what it believes it is
       │               │
       └───────┬───────┘
               ▼
          divergence
```

That divergence may itself become a scientific observable.

A mature Symbiont should not necessarily have perfect self-knowledge.

It should have a developed, revisable and bounded model of itself.

---

# 36. Recommended implementation sequence

The recommended PR sequence is:

```text
PR 1
refactor(observatory): split state, projection and render layers

PR 2
feat(observatory): replace fixed cell with deterministic phenotype morphology

PR 3
feat(observatory): add phenotype/self perspective

PR 4
feat(self): introduce sensory digital body schema

PR 5
feat(observatory): render organism-owned body schema

PR 6
feat(self): learn coarse cognitive regions and dependencies
```

Do not combine all six into one PR.

The main architectural rule is:

> **The Observatory may know more about a Symbiont than the Symbiont knows about itself, but it must never pretend that privileged knowledge belongs to the organism.**

And the corresponding visual rule is:

> **Morphology represents organization. Geometry is a projection, not the organism's ontology.**
