# Symbiont Lab — GAP Analysis against Experience & World Architecture Specification v1

**Status:** Implementation GAP Analysis  
**Target specification:** *Symbiont Lab — Experience & World Architecture Specification v1*  
**Repository:** `alessbarb/symbiont-lab`  
**Baseline reviewed:** `main` at `4671cb39078fc0788ed4d9e489a118aa6b24ae73`  
**Date:** 2026-09-28  
**Scope:** Core organism boundaries, Physics3D, Workbench/Observatory, run persistence, Embodiment, Vision, World, Home, Mind, Archive, causal provenance, reproducibility and observability performance.

---

## 1. Executive conclusion

The current codebase is **architecturally closer to the target specification than the existing Workbench product model suggests**.

The largest implementation gap is no longer the Symbiont core. Core already contains strong foundations for:

- separation of `Symbiont`, `Body` and `EmbodimentEpisode`;
- embodiment epochs;
- body death as an explicit embodiment termination reason;
- re-embodiment;
- body-schema acquisition;
- sensorimotor causal evidence;
- competence development;
- observer/organism epistemic separation;
- persistent causal provenance;
- deterministic Physics3D execution;
- reproducible physical environment recipes;
- portable organism checkpoints.

In addition, the recent performance program **P0–P7** materially changes the implementation strategy for Experience & World Architecture v1.

The repository now has a strong passive-observation architecture:

```text
PHYSICS / ORGANISM CAUSAL PATH
            │
            ├── causal ticks
            ├── learning
            ├── cognition
            ├── BodySchema
            ├── physiology
            └── provenance
            │
──────────── observer boundary ────────────
            │
            ├── bounded observer projections
            ├── independent observation cadence
            ├── anchor/delta live transport
            ├── serialized-once SSE
            └── bounded browser rendering
```

Therefore **Experience & World Architecture must be implemented on top of these boundaries, not by introducing a parallel runtime, snapshot system or observation pipeline**.

The remaining architectural work is concentrated in five areas:

1. **Run ontology** — the Lab still lacks first-class `Experience` versus `World` execution semantics.
2. **Product/domain decomposition** — `Body`, `Mind`, `In World` and `Experiments` still mix responsibilities that the target architecture separates.
3. **Protected acquisition** — Embodiment/Vision acquisition safety is not formalized.
4. **Vision** — there is no causal visual apparatus or visual acquisition domain yet.
5. **Integrated World** — Physics3D already has world geometry and observer truth, but there is no first-class Challenge World / Acquired World integration aligned with the specification.

The implementation should therefore be treated primarily as an **ontology and domain-boundary refactor plus one major new causal capability (Vision)**.

---

# 2. Normative target

The specification defines the primary architectural principle as:

> **Experience acquires capability. World integrates capability.**

The code must ultimately make the following distinctions explicit:

```text
Experience
    controlled acquisition
    non-terminal body envelope
    isolates a discoverable relationship

World
    integrated challenge
    complete environmental consequences
    may terminate the Body

Mind
    transversal cognitive observation

Archive
    developmental and scientific history

Observer
    passive projection only
```

The implementation must also preserve:

```text
physical truth
≠ apparatus-transduced signal
≠ organism-acquired structure
≠ observer interpretation
```

---

# 3. Current architecture snapshot

## 3.1 Core embodiment

Current canonical implementation:

```text
src/symbiont/core/embodiment/
```

`EmbodimentEpisode` already represents:

```text
symbiont_id
body_id
embodiment_id
epoch
start/end Symbiont tick
state
end reason
BodySchema
SensorimotorDynamicsModel
CausalEvidenceLedger
CompetenceEffectModel
ControllabilityModel
AgencyModel
adaptation
reachability
execution bindings
embodiment prior
contract history
```

Current states:

```text
ACTIVE
SUSPENDED
CLOSED
```

Current termination reasons include:

```text
BODY_DEATH
BODY_REPLACED
DETACHED
LOST
EXPLICIT_MIGRATION
UNRECOVERABLE_CONTRACT_LOSS
```

This is already strongly aligned with sections 2.8, 3.2, 3.3, 6.8 and 20 of the target specification.

### Assessment

**Status: ALIGNED — preserve.**

Do not introduce an `ExperienceEmbodiment` object into Symbiont core.

`EmbodimentEpisode` is biographical organism/body coupling.

An `Embodiment Experience` is a Lab execution context over that coupling.

These are distinct concepts.

---

## 3.2 Re-embodiment

Current:

```text
src/symbiont/core/embodiment/reembodiment.py
```

Already provides:

```text
select_prior()
begin_reembodiment()
replace_body()
```

Historical priors are intentionally not installed as factual state.

This directly supports the specification's requirement that retained information across bodies acts as evidence/candidate structure rather than fabricated body truth.

### Assessment

**Status: ALIGNED — preserve and expose correctly in Lab lifecycle.**

Main missing work is orchestration/UI:

```text
World body non-viable
→ close EmbodimentEpisode(BODY_DEATH)
→ persist dormant Symbiont
→ Home exposes re-embodiment
→ bind fresh Body
→ begin next embodiment epoch
→ Embodiment Experience / reacclimation
```

---

# 4. Performance architecture P0–P7

The recent optimization program is now a hard dependency of this architecture.

It should be treated as an invariant.

## 4.1 P1 — observability extracted from organism hot path

`OrganismRuntime.tick(include_observability=False)` preserves the causal organism step while omitting human-facing projections.

Causal work remains:

- perception;
- learning;
- cognition;
- action;
- BodySchema;
- physiology;
- development;
- causal provenance;
- bounded life journal.

Human-readable narratives and aggregate projections can be omitted.

### Impact on Experience architecture

The target architecture **must not reintroduce Experience-specific rich projection work into every causal tick**.

Forbidden design:

```text
each Symbiont tick
→ build full EmbodimentExperienceSnapshot
→ build full VisionExperienceSnapshot
→ build full WorldSnapshot
```

Required design:

```text
causal state
→ passive projection only when observation cadence requires it
```

---

## 4.2 P4 — independent clocks

Current architecture formally separates:

```text
physics_hz
cognition_hz
observation_hz
render_hz
```

Current documented default Physics3D values:

```text
physics       240 Hz
cognition      24 Hz
observation    12 Hz
render         60 Hz
```

The rates are deterministically scheduled and do not require observation/render cadence to equal cognition cadence.

### Impact

All new Experiences and World views must obey:

```text
causal sampling
≠ scientific observation
≠ visual presentation
```

Vision in particular must not conflate:

```text
Symbiont visual sampling
with
human POV rendering
```

---

## 4.3 P5 — anchor/delta live observation

Current live observer transport supports:

```text
observer-live-delta-v1
```

for channels such as:

```text
body
cognition
vitals
mind_snapshot
observed_frame
```

with:

```text
anchor
delta
revision
base_revision
recovery after gaps
recovery after overflow
```

`world_scene` intentionally retains its own revisioned domain contract.

### Impact

No new Experience should create a competing live state protocol without evidence that the existing transport cannot support it.

---

## 4.4 P6 — serialized-once SSE

`ObservationBus` now owns serialized observer bytes and transport identity separately.

SSE no longer reparses and reserializes observer JSON.

Opportunistic batching reduces writes without introducing a fill-delay.

### Impact

Any new live Vision/Embodiment/World observer channel should enter the existing bus architecture.

---

## 4.5 P7 — bounded browser work

Recent Workbench changes make cognition layout and DOM updates bounded:

- deterministic spatial buckets;
- removal of explicit all-pairs local layout work;
- no repeated per-node full edge scans;
- reduced canvas shadow cost;
- summary updates decoupled from RAF;
- Body workspace ignores unchanged metric values.

### Impact

New UI must preserve:

```text
RAF animation
≠ data-model recomputation
≠ DOM summary refresh
```

---

## 4.6 New invariant required by this GAP

Add the following architecture requirement to Experience & World implementation:

### Observability Independence

For matched executions with the same:

```text
starting causal checkpoint
seed
physics configuration
causal rate plan
Experience/World definition
```

observer-enabled and observer-disabled runs must preserve identical causal outcomes within the project's declared determinism guarantees.

Compare at minimum:

```text
organism state hash
actions / actuation
Body state
causal provenance
competence state
acquired structures
embodiment lifecycle
```

---

# 5. GAP matrix

Legend:

- **ALIGNED** — already satisfies the target materially.
- **PARTIAL** — foundation exists but target contract is incomplete.
- **MISSING** — target abstraction/capability does not exist.
- **MISPLACED** — capability exists but resides in the wrong product/domain boundary.
- **DO NOT DUPLICATE** — recent architecture already solves the problem.

| Spec area | Current state | Classification | Required work |
|---|---|---|---|
| Symbiont / Body separation | Strong core separation | ALIGNED | Preserve |
| Embodiment epoch | Implemented | ALIGNED | Expose in run/UI model |
| Body death reason | Implemented | ALIGNED/PARTIAL | Connect to World termination |
| Re-embodiment | Implemented | ALIGNED/PARTIAL | Product/run lifecycle |
| Observer truth isolation | Strong observer contracts | ALIGNED | Extend to Vision |
| Observability independence | P0/P1 foundation | ALIGNED | Make release invariant |
| Independent clocks | P4 | ALIGNED | Reuse |
| Live delta transport | P5 | DO NOT DUPLICATE | Reuse |
| SSE transport | P6 | DO NOT DUPLICATE | Reuse |
| Bounded browser render | P7 | DO NOT DUPLICATE | Apply patterns |
| Run kind | No `Experience`/`World` ontology | MISSING | Introduce |
| State-X reproducible start | Checkpoints/hashes partly exist | PARTIAL | Immutable run start reference |
| ExperienceDefinition | No first-class abstraction | MISSING | Add Lab-level definition |
| ExperienceSnapshot | Spec recommends concept | SHOULD NOT BE UNIVERSAL | Use passive projections instead |
| Acquisition safety | No formal policy | MISSING | Add Lab policy |
| World consequence policy | Implicit physical behavior | PARTIAL | Formalize |
| Embodiment Experience | Core exists; UI still `Body` | MISPLACED | Reframe |
| Action Discovery | Motor Learning exists in Mind | MISPLACED | Move/reframe |
| Acquired Self | Self-model exists | PARTIAL/MISPLACED | Reframe |
| Vision apparatus | No causal visual apparatus | MISSING | Implement |
| Vision acquisition | No visual learning substrate | MISSING | Implement after apparatus |
| Vision UI | No view | MISSING | Implement last |
| World physical scene | Exists under Body | MISPLACED | Extract |
| Challenge World | Environment recipes exist | PARTIAL | Add challenge manifest/definition |
| Acquired World | Not canonical | MISSING/PARTIAL | Build only from organism evidence |
| World Compare / Truth | Observer truth exists | PARTIAL | New World UI projection |
| Mind purity | Mind owns motor/sensory/history | MISPLACED | Refactor |
| Home developmental model | Launcher-oriented | PARTIAL | Refactor |
| Archive developmental history | Run list + journals exist | PARTIAL | Build projections/indexes |
| Lab/Experiments navigation | Still top-level | MISPLACED | Remove after functionality inventory |
| Causal trace physical→acquired | Strong mid-chain provenance | PARTIAL | Extend apparatus-side correlation |
| Generalization evidence | Studies infrastructure exists | PARTIAL | Formalize gates |
| World yincana | contact-garden exists | PARTIAL | Build reproducible integrated challenge |

---

# 6. Run ontology GAP

## 6.1 Current code

Current principal Workbench launch contract:

```text
Physics3DLaunchSpec
```

contains:

```text
run_id
organism_ref
body_ref
body_kind
organism_mode
body_mode
symbiont_file
body_file
telemetry_file
environment
```

Current manifest stores:

```text
status
started_at
ended_at
compatibility
previous_body_kind
receptor/effectors/motor_dof contract
```

The current bundle summary already includes useful newer fields:

```text
checkpoint_id
checkpoint_hash
manifest_generated_from_checkpoint_hash
symbiont_state
embodiment_epoch
body_id
embodiment_id
```

This is important: state identity is now stronger than in the older analysis.

## 6.2 Target GAP

The Lab cannot currently distinguish:

```text
acquisition.embodiment
acquisition.vision
world.challenge
world.open
```

as execution semantics.

There is no formal:

```text
RunKind
ExperienceDefinitionRef
WorldDefinitionRef
AcquisitionSafetyPolicy
WorldConsequencePolicy
TerminationReason taxonomy
```

at the Lab run level.

## 6.3 Required change

Introduce a Lab-level run descriptor above `Physics3DLaunchSpec`.

Recommended:

```text
RunKind
    ACQUISITION_EMBODIMENT
    ACQUISITION_VISION
    WORLD_CHALLENGE
    WORLD_OPEN
```

Do not make these strings cognition-visible.

Recommended separation:

```text
RunDefinition
    ↓
Physics3DLaunchSpec
```

`Physics3DLaunchSpec` remains an adapter/execution DTO.

---

# 7. State-X / reproducibility GAP

The specification requires:

```text
R = execute(X, Environment, Config, Seed)
```

where X is a precise reproducible organism state.

## Current strengths

The code already persists portable Symbiont state and physical body state.

Bundle manifests now expose checkpoint IDs/hashes.

Physics3D verifies organism/body temporal continuity on restore.

Environment recipes are immutable/versioned and resume refuses incompatible world replacement.

## Remaining GAP

The run manifest still fundamentally references the evolving organism slot:

```text
organism_ref
```

A scientific run must be able to identify **the exact starting causal state**, not merely the subject directory.

### Required

Persist:

```text
starting_checkpoint_id
starting_checkpoint_hash
starting_body_checkpoint_hash
ending_checkpoint_id
ending_checkpoint_hash
```

or immutable references providing equivalent guarantees.

Do not copy observer layout state into X.

State X includes causal continuation state only.

It must exclude:

```text
Cognition Atlas coordinates
UI filters
observer narrative
DOM state
presentation camera
observer-derived semantics
```

---

# 8. Experience abstraction GAP

## Current state

No `ExperienceDefinition` exists as a first-class Lab concept.

The term `experience` is already used elsewhere for organism/private experience records and studies. The new architecture must avoid semantic collision.

## Required abstraction

Recommended Lab namespace:

```text
src/symbiont_lab/experience/
    __init__.py
    definition.py
    manifest.py
    safety.py
    catalog.py
```

Conceptually:

```text
ExperienceDefinition
    id
    kind
    apparatus requirements
    protected environment definition
    causal rate requirements
    observer scientific purpose
    safety policy
    seed/config
```

### Important correction to the original spec

Do **not** introduce a universal heavy `ExperienceSnapshot`.

The P0–P7 architecture makes that unnecessary and potentially harmful.

Use:

```text
causal state
→ domain-specific passive observer projection
→ ObservationBus
```

---

# 9. Acquisition safety GAP

The spec requires Acquisition Experiences to be non-terminal.

## Current state

Physics3D supports:

- Living Body state;
- metabolic reserve;
- body ageing/senescence;
- physical consequences;
- body death semantics at Embodiment level.

There is currently no explicit run policy stating:

```text
this run is protected acquisition
```

versus:

```text
this run is full-consequence World
```

## Required behavior

Introduce:

```text
AcquisitionSafetyPolicy
```

The recommended implementation is **not** to silently repair a dying body during a causal sequence.

Preferred lifecycle:

```text
body approaches protected viability boundary
    ↓
acquisition termination condition
    ↓
run ends as protected_recovery
    ↓
causal checkpoint remains coherent
```

Then the Lab may establish the next controlled acquisition state.

This avoids:

```text
hidden magical repair
→ unexplained sensory transition
→ contaminated evidence
```

## Explicit prohibition

An acquisition policy must never modify:

```text
action choice
reward
cognitive evidence
causal relation confidence
```

in order to produce desired researcher behavior.

---

# 10. Embodiment Experience GAP

## 10.1 Existing strengths

The causal substrate is already strong:

```text
EmbodimentEpisode
BodySchemaEngine
SensorimotorDynamicsModel
CausalEvidenceLedger
CompetenceEffectModel
ControllabilityModel
AgencyModel
EmbodimentAdaptation
ReachabilityModel
CompetenceExecutionBindingRegistry
```

No new core Embodiment system is required.

## 10.2 Product mismatch

Current Workbench still exposes:

```text
Body
```

and mixes:

```text
world
anatomy
motion
physiology
interaction
history
self-model
```

The target requires Embodiment to answer only:

> What can this organism discover about acting through this apparatus?

## 10.3 Required migration

### Remain in Embodiment

```text
anatomical-visual.js
model.js
self-model.js
self-view.js
morphology-neutral renderer
apparatus activity
BodySchema correspondence
interoception
action/consequence evidence
competence development
```

### Leave Embodiment

```text
world-view.js
world-state.js
global trajectory
external geometry
resource-distance presentation
navigation-oriented interpretation
environment interaction semantics
```

Move these to World.

---

# 11. Action Discovery / Mind GAP

Current Mind owns:

```text
motor-learning.js
motor-learning-model.js
motor-learning-chart.js
motor-learning-history.js
```

This violates the target boundary.

## Required refactor

User-facing terminology:

```text
Motor Learning
→ Action Discovery / Sensorimotor Discovery
```

The internal technical classes such as `MotorCompetence` do not need automatic renaming if they remain semantically correct.

Move presentation and domain ownership to Embodiment.

Mind may show causal links to these structures but must not own the body-specific acquisition surface.

---

# 12. Acquired Self GAP

Current `self-model.js` / `self-view.js` provide a strong base.

The required conceptual correction is:

```text
rendered anatomical ghost
≠ automatically "what Symbiont thinks its body looks like"
```

The target `Acquired Self` must represent evidence-supported correspondence.

Observer morphology may be used to project that evidence, but the UI must mark the projection as observer-side correspondence.

Recommended modes:

```text
Knowledge
Stability
Controllability
Uncertainty
```

Avoid presenting anatomical completion as inherent organism semantics.

---

# 13. Vision — major causal GAP

This remains the largest new capability.

## Current state

Physics3D has:

- physical geometry;
- render infrastructure;
- observer world scene;
- body apparatus;
- opaque receptor contracts;
- deterministic rates.

But there is no canonical visual apparatus through which Symbiont receives visual signals.

`world_scene` and observer geometry are **not** valid substitutes.

## Required architecture

```text
Physics world
    ↓
VisualApparatus
    ↓
physical visual sample
    ↓
opaque visual receptor channels
    ↓
EmbodimentContract perceptual surface
    ↓
Symbiont cognition
```

Forbidden:

```text
PhysicsWorldObserver.entities
→ visual source identity
→ Symbiont
```

---

# 14. Visual apparatus topology GAP

The target spec permits physical receptor adjacency to be apparatus-given while source grouping remains acquired.

Current opaque contracts do not yet clearly formalize perceptual topology as a causal apparatus fact.

This requires an explicit design decision.

Recommended new neutral structure:

```text
PerceptualTopology
```

Possible information:

```text
channel adjacency
array dimensions
neighbour relation
surface membership
```

Must exclude:

```text
object IDs
semantic labels
depth
distance
"left eye" human semantics unless observer-only
RGB semantic names as cognitive categories
```

This deserves an ADR before implementation.

---

# 15. Vision observation and P0–P7

Vision must be designed around the new rate architecture.

Example:

```text
physics                    240 Hz
cognition / organism         24 Hz
visual causal sampling       causal contract-defined rate
scientific Vision projection 12 Hz
human animation              60 Hz
```

No assumption that human rendering frequency is the organism sampling rate.

## Dense receptor-field warning

`observer-live-delta-v1` replaces changed arrays atomically.

A 32×32 receptor field may change almost entirely every sample.

Therefore raw receptor visualization must be benchmarked rather than assumed to fit efficiently into generic JSON deltas.

Possible observer-only presentation solutions:

```text
packed binary field
domain-specific frame channel
sparse event encoding if the apparatus supports event semantics
```

This is an observer transport decision only.

It must not change the organism's causal visual input.

---

# 16. World extraction GAP

## Current state

The repository already contains a strong observer-only world representation:

```text
src/symbiont_lab/observation/world_scene.py
```

and a revisioned `world_scene` transport contract.

`PhysicsWorldObserver` explicitly states it is read-only spatial truth and never a world model given to Symbiont.

This is strongly aligned with observer-truth isolation.

## Product mismatch

World rendering currently sits inside:

```text
views/body/world-view.js
views/body/world-state.js
```

and appears as part of Body.

## Required refactor

Create:

```text
views/world/
```

and move ownership of:

```text
external entities
global pose context
trajectory
environment geometry
contacts with external sources
challenge regions
observer truth
```

there.

### Preserve

Do not rewrite the existing `world_scene` revision protocol simply to move the UI.

This is a presentation/domain ownership extraction.

---

# 17. Challenge World / yincana GAP

Current environments:

```text
flat-v1
contact-garden-v1
```

are already:

- versioned;
- immutable;
- persisted with physical state;
- rejected on incompatible resume;
- not injected into cognition.

This is an excellent foundation.

`contact-garden-v1` already provides:

```text
varying friction
low surface
smooth surface
block
barrier
```

but it is not yet a formal Challenge World.

## Required abstraction

Add observer-only:

```text
ChallengeWorldDefinition
```

containing:

```text
world_id
version
environment recipe
seed
challenge regions / situations
observer scientific purpose
perturbation schedule
```

Symbiont must not receive challenge identifiers or researcher purposes.

### Do not encode

```text
correct route
goal point
task reward
success path
win condition
```

---

# 18. World consequence completeness GAP

Core already understands body death.

Run orchestration still lacks the formal rule:

```text
World:
no protected acquisition rescue
```

Required World termination:

```text
body viability lost
→ close EmbodimentEpisode(BODY_DEATH)
→ persist organism
→ lifecycle state dormant
→ terminate run: body_non_viable
```

The replacement body must not silently appear during the same World run.

---

# 19. Acquired World GAP

The current observer has physical truth.

The target requires a separate:

```text
Acquired World
```

constructed only from organism evidence.

This does **not** currently exist as a mature canonical World model.

It must not be synthesized directly from `PhysicsWorldObserver.entities`.

Required principle:

```text
observer entity
may be correlated to
organism-acquired source

but correlation
must remain observer-side
```

Acquired World candidates should derive from:

```text
visual evidence
contact evidence
action consequences
persistence evidence
predictions
cross-modal relations
```

when those capabilities actually exist.

---

# 20. World UI GAP

Target modes:

```text
Acquired
Compare
Observer Truth
```

## Acquired

Only organism-supported external structure.

## Compare

Observer correlation between acquired structure and physical truth.

## Observer Truth

Full physical scene, prominently marked observer-only.

The current `world_scene` can supply Truth.

Compare and Acquired require new projection logic.

---

# 21. Mind GAP

Current Mind is too broad.

It includes:

```text
Overview
Identity/Sensory
Cognition
Motor Learning
History
```

Target responsibility:

```text
concepts
predictors
relations
attention
memory
generative cognition
uncertainty
structural change
causal provenance
```

## Required redistribution

```text
global organism overview
→ Home

body schema / phenotype correspondence
→ Embodiment

proprioception / interoception apparatus
→ Embodiment

motor discovery
→ Embodiment

visual apparatus
→ Vision

full longitudinal history
→ Archive

cognitive interpretation/use of signals
→ Mind
```

The recent P7 cognition optimization should be preserved during this refactor.

---

# 22. Home GAP

Current Home is still primarily a Physics3D run launcher.

It already has useful concepts:

```text
body selection
existing/new organism
fresh/resume body
environment
compatibility
recent runs
```

Target Home must instead answer:

> Who is the current Symbiont and where is it developmentally?

## Required state

```text
organism identity
developmental age/tick
lifecycle
current embodiment epoch
body
current run kind
capability summary
recent developmental changes
dormant/active state
```

## Required launch semantics

Launch:

```text
Embodiment Experience
Vision Experience
World Challenge
World Open
```

from an explicit checkpoint/state X.

Home must use a compact status projection rather than subscribing to all rich observer channels.

---

# 23. Archive GAP

Current Archive is primarily run history.

Target Archive is developmental scientific history.

Required indexable dimensions:

```text
organism lineage
checkpoints
embodiment epochs
Experience runs
World runs
body deaths
re-embodiments
capability acquisition/revision
seeds/configuration
causal histories
comparisons
```

## Important consequence of P3

Archive must not reconstruct history by full live journal replay.

Use:

```text
indexed EventJournal access
checkpoint index
run manifests
paged provenance
```

The P3 age-independent journal architecture makes long-lived organisms feasible and must not be regressed.

---

# 24. Lab / Experiments GAP

Current Workbench routing still contains:

```text
experiments → mountLab()
lab → experiments alias
```

Target architecture removes generic Lab/Experiments from organism-facing primary navigation.

This does **not** mean deleting research infrastructure.

Required sequence:

1. inventory all functionality under `views/lab`;
2. classify:
   - run creation → Home;
   - study/history result → Archive;
   - environment configuration → Experience/World launch;
   - specialist research controls → dedicated research tooling if still necessary;
3. remove top-level route only after ownership is reassigned.

---

# 25. Causal provenance GAP

Current causal provenance is strong in organism acquisition/action.

The target chain is:

```text
physical event
→ apparatus state
→ receptor sample
→ opaque signal
→ cognitive evidence
→ acquired relation
→ prediction / competence / source
→ future consequence
```

The remaining weak area is the **physical/apparatus beginning of the chain**, especially for future Vision.

Recommended observer correlation keys:

```text
tick
apparatus id
receptor id
sample id
signal id
causal provenance ref
```

Physical truth links remain observer-only.

---

# 26. Snapshot contract correction

The target spec proposes future snapshots separating:

```text
truth
apparatus
organism_evidence
acquired_structure
observer_correspondence
```

The conceptual separation is correct.

The implementation should **not** necessarily materialize all five as one monolithic object.

Prefer separate passive projections/channels with explicit provenance and revisions.

For example:

```text
apparatus projection
acquired structure projection
observer truth / world_scene
observer correspondence on demand
```

This is more consistent with P0–P7 and avoids rebuilding huge state.

---

# 27. Metrics GAP

The target spec's metrics philosophy is compatible with current sensorimotor research infrastructure.

## Embodiment

Primary:

```text
causal relations
repeatability
predictive utility
controllability
competence maturity
uncertainty
transfer/reacquisition
```

Do not prioritize:

```text
distance
speed
resource progress
walking
```

Those current Physics3D fields may remain diagnostics or World-level behavior measurements.

## Vision

New metrics required:

```text
temporal predictive utility
coherence
persistence
occlusion recovery
transformation prediction
self-caused vs unexplained change
generalization
uncertainty calibration
```

## World

Required integration metrics:

```text
capabilities recruited
cross-modal evidence
prediction validity
discrepancies
revision
unexplained observations
generalization
recovery
```

No single overall reward/score.

---

# 28. Generalization and ablation GAP

The repo already has strong preregistered study conventions and matched-seed experiments.

This is a major asset.

The new architecture should formalize studies such as:

```text
same X
→ World W with no Vision acquisition

same X
→ Vision Experience
→ World W
```

with matched World seeds.

Likewise:

```text
same X
→ Embodiment Experience
→ W

versus

same X
→ W
```

Capability claims should use existing scientific discipline:

```text
pre-registration
held-out seeds
explicit gates
negative results retained
```

---

# 29. Required new ADRs

Before major code movement, create the following ADRs.

## ADR-EW-001 — Experience versus World execution

Defines:

```text
Acquisition Experience
World
RunKind
protection semantics
consequence semantics
```

## ADR-EW-002 — State-X and immutable run provenance

Defines:

```text
starting checkpoint identity
body checkpoint identity
hashes
seed/config
end-state identity
```

## ADR-EW-003 — Observer architecture preservation

Makes P0–P7 requirements normative for all future Experience/World work.

## ADR-EW-004 — Visual apparatus and perceptual topology

Defines:

```text
visual apparatus boundary
opaque channels
topology exposure
sampling
observer truth
```

## ADR-EW-005 — Acquired World versus observer truth

Defines legal correlation paths and explicitly forbids physics-entity injection.

---

# 30. Revised implementation plan

The original spec's phase order remains broadly correct but should be adjusted for the optimized codebase.

## Phase 0 — Preserve performance architecture

**Goal:** freeze P0–P7 as architectural invariants.

Deliverables:

- ADR-EW-003;
- boundary tests for new run kinds;
- no new observer work in causal hot path;
- no parallel SSE/observer bus.

**Risk:** Low.

---

## Phase 1 — Run ontology and State-X

Implement:

```text
RunKind
RunDefinition
starting checkpoint identity/hash
ending checkpoint identity/hash
termination reason
definition reference
seed/config
rate plan
```

Preserve `Physics3DLaunchSpec` as adapter.

**Risk:** Medium.

---

## Phase 2 — Experience contract and acquisition safety

Implement Lab-level:

```text
ExperienceDefinition
ExperienceKind
AcquisitionSafetyPolicy
protected termination reason
```

Do not create a second organism runtime.

**Risk:** Medium.

---

## Phase 3 — Extract World from Body

Move presentation ownership:

```text
body/world-view.js
body/world-state.js
→ views/world/
```

Preserve `world_scene` protocol.

Add Workbench route:

```text
world
```

Do not yet invent Acquired World.

**Risk:** Low–Medium.

---

## Phase 4 — Embodiment Experience UI

Rename conceptual Body → Embodiment.

Replace current mixed tabs with:

```text
Discovery
Apparatus
Acquired Self
```

Move Action Discovery presentation from Mind.

Remove World metrics as primary Embodiment metrics.

Reuse current observer channels.

**Risk:** Medium.

---

## Phase 5 — Mind cleanup

Remove:

```text
motor acquisition
body apparatus
body physiology
full history
```

Keep cognition.

Preserve P7 spatial-index/render architecture.

**Risk:** Medium.

---

## Phase 6 — Visual apparatus

Implement causal:

```text
VisualApparatus
visual sampling
opaque visual receptors
apparatus health
perceptual topology contract
```

No Vision UI required yet.

Add epistemic boundary tests.

**Risk:** High.

---

## Phase 7 — Vision acquisition

Establish progressively:

```text
temporal predictability
local coherence
transformations
source candidates
persistence
occlusion
self-caused relation
independent change
```

Do not require object recognition.

**Risk:** High.

---

## Phase 8 — Vision observation/UI

Add bounded scientific projections.

Benchmark raw receptor field transport separately.

Add:

```text
Discovery
Apparatus
Acquired
```

**Risk:** Medium.

---

## Phase 9 — Challenge World v1

Formalize `ChallengeWorldDefinition`.

Build first reproducible yincana using existing environment recipe infrastructure.

Suggested challenge families:

```text
support variation
occlusion
independent visual change
constrained geometry
multimodal contact
combined novelty
```

No goals or semantic tasks.

**Risk:** High.

---

## Phase 10 — World lifecycle completeness

Implement:

```text
body non-viable
→ BODY_DEATH
→ embodiment epoch close
→ dormant Symbiont
→ World run termination
```

Then Home can initiate re-embodiment.

**Risk:** Medium.

---

## Phase 11 — Acquired World / Compare

Only after Vision + cross-domain evidence exists.

Implement:

```text
Acquired
Compare
Observer Truth
```

Never synthesize Acquired directly from physics ground truth.

**Risk:** High.

---

## Phase 12 — Archive

Build developmental history over:

```text
run manifests
checkpoint hashes
embodiment epochs
indexed journals
provenance
```

No full-history live scans.

**Risk:** Medium.

---

## Phase 13 — Home final

Convert launcher into organism developmental home.

**Risk:** Low–Medium.

---

## Phase 14 — Remove generic Experiments route

Only after all functionality has a new owner.

**Risk:** Low.

---

# 31. Dependencies

```text
P0–P7 observability architecture
            │
            ▼
Run ontology / State-X
            │
            ▼
Experience contract + Safety
            │
       ┌────┴─────┐
       ▼          ▼
Embodiment      World extraction
       │          │
       └────┬─────┘
            ▼
      Vision apparatus
            │
            ▼
     Vision acquisition
            │
            ▼
      Challenge World
            │
            ▼
 multimodal Acquired World
            │
       ┌────┴─────┐
       ▼          ▼
    Archive      Home final
```

---

# 32. Release gates mapped to current code

## Gate A — Epistemic isolation

**Foundation exists.**

Required new tests:

```text
visual ground-truth boundary
challenge metadata boundary
observer-correlation boundary
```

---

## Gate B — Causal trace

**Partial.**

Current provenance covers much of acquisition/action.

Need a complete apparatus-origin trace, especially Vision.

---

## Gate C — Embodiment acquisition

**Largely exists.**

Sensorimotor acquisition and competence evidence are already strong.

UI/domain representation must be corrected.

---

## Gate D — Vision acquisition

**Missing.**

Cannot pass until a real VisualApparatus and predictive visual acquisition exist.

---

## Gate E — Transfer

**Infrastructure exists; Experience-specific protocols missing.**

Use matched state X and held-out conditions.

---

## Gate F — World integration

**Missing as target architecture.**

Physical interaction exists; explicit integration of independently acquired domains does not yet.

---

## Gate G — Consequence lifecycle

**Core primitives exist; Lab lifecycle incomplete.**

Need World body death → dormant run semantics.

---

## Gate H — Replay

**Strong foundation.**

Checkpoint, persistence, deterministic environment and journal work exist.

Need RunDefinition/State-X completeness.

---

## New Gate I — Observability independence

Required for every new Experience/World run kind.

---

## New Gate J — Age-independent observation/history

No live projection may introduce work proportional to complete organism/world history.

---

# 33. Files/modules likely affected

## Core — minimal changes expected

```text
src/symbiont/core/embodiment/contract.py
src/symbiont/core/embodiment/episode.py
```

Only if required for perceptual topology / explicit visual surface semantics.

Avoid broad core rewrites.

---

## Lab runtime

```text
src/symbiont_lab/app/physics3d/runs.py
src/symbiont_lab/app/physics3d/session.py
src/symbiont_lab/physics3d/engine.py
src/symbiont_lab/physics3d/runtime.py
src/symbiont_lab/physics3d/environments.py
```

New likely namespace:

```text
src/symbiont_lab/experience/
src/symbiont_lab/world_challenge/   # or equivalent unambiguous name
src/symbiont_lab/physics3d/vision/
```

Do not overload existing `src/symbiont_lab/world/` until its current population/genesis semantics are audited.

---

## Observation

Preserve:

```text
src/symbiont_lab/observation/bus.py
src/symbiont_lab/observation/delta.py
src/symbiont_lab/observation/cadence.py
src/symbiont_lab/observation/contracts.py
src/symbiont_lab/observation/world_scene.py
```

Extend only where needed.

---

## Workbench

Current:

```text
views/body/
views/mind/
views/home.js
views/archive/
views/lab/
```

Target:

```text
views/embodiment/
views/vision/
views/world/
views/mind/
views/home/
views/archive/
```

Shared infrastructure should remain shared rather than copied.

---

# 34. Naming collision warning: existing `symbiont_world`

The repository already contains:

```text
src/symbiont_world/
src/symbiont_lab/world/
```

with population/genesis/event/runtime semantics.

The target `World` is specifically the integrated embodied environment defined by Experience & World Architecture v1.

Do not assume the existing package is equivalent.

Before naming new modules, perform a dedicated audit.

Recommended temporary distinction:

```text
IntegratedWorld / ChallengeWorld
```

at implementation level if necessary, while the product UI remains `World`.

---

# 35. Explicit non-goals

The implementation must not:

1. rewrite Embodiment core merely to match new UI naming;
2. introduce a second observer bus;
3. create monolithic Experience snapshots per causal tick;
4. use `world_scene` entities as organism visual input;
5. make Challenge World a task/reward benchmark;
6. expose researcher challenge IDs to Symbiont;
7. treat World body death as punishment;
8. silently respawn a body mid-World;
9. equate Vision with RGB camera rendering;
10. treat anatomical observer names as acquired body semantics;
11. rebuild full history in live paths;
12. regress P0–P7 performance boundaries.

---

# 36. Critical implementation decisions

Before coding begins, the following decisions should be closed formally.

### D1. Exact RunKind model

Recommended:

```text
acquisition.embodiment
acquisition.vision
world.challenge
world.open
```

### D2. Acquisition protection boundary

Recommended:

```text
terminate before irreversible viability loss
```

rather than invisible causal repair.

### D3. Visual topology

Recommended:

```text
physical receptor adjacency available
semantic grouping not available
```

### D4. Visual raw-field observer transport

Benchmark after apparatus exists.

Do not preselect generic JSON delta.

### D5. Existing `symbiont_lab/world` relationship

Audit before reuse/rename.

### D6. Acquired World ownership

Must derive from organism evidence, not from Observatory synthesis.

---

# 37. Final GAP assessment

## Already strong

```text
Symbiont/Body/Embodiment separation
Embodiment epochs
re-embodiment
body death semantics
sensorimotor discovery
BodySchema
competence evidence
ground-truth isolation
causal provenance
portable persistence
reproducible physical fixtures
observer/cause separation
independent execution rates
efficient live observation
browser performance boundaries
```

## Needs refactoring

```text
Body → Embodiment
In World → World
Motor Learning → Embodiment / Action Discovery
Identity/Sensory decomposition
Home semantics
Mind semantics
Archive semantics
Lab/Experiments navigation
```

## Needs new architecture

```text
RunKind
ExperienceDefinition
State-X run identity
AcquisitionSafetyPolicy
WorldConsequencePolicy
ChallengeWorldDefinition
termination taxonomy
```

## Needs new causal capability

```text
VisualApparatus
visual receptor topology
visual acquisition
visual source/persistence structure
cross-modal visual integration
```

## Must explicitly preserve

```text
P0–P7 observability/performance architecture
world_scene revision contract
indexed World journal
portable organism authority
observer-only truth boundary
```

---

# 38. Recommended first implementation milestone

The first milestone should **not** attempt Vision.

### Milestone EW-A — Architecture Foundation

Deliver:

1. ADR Experience vs World.
2. ADR P0–P7 observability invariants.
3. `RunKind`.
4. Run manifest/state-X identity.
5. explicit termination reasons.
6. `ExperienceDefinition`.
7. `AcquisitionSafetyPolicy`.
8. `WorldConsequencePolicy`.
9. Workbench `World` route extracted from `Body`.
10. rename product-facing `Body` → `Embodiment`.
11. no behavior change to Symbiont cognition.
12. observability-independence gate remains green.

### Acceptance

The milestone is complete when the same current Physics3D organism can run with unchanged causal behavior while the Lab can truthfully say whether it is executing:

```text
an Embodiment acquisition
or
a World run
```

and the UI no longer presents World as part of Body.

---

# 39. Recommended second milestone

### Milestone EW-B — Embodiment Experience

Deliver:

```text
Discovery
Apparatus
Acquired Self
```

Move Action Discovery from Mind.

Formalize protected acquisition termination.

Remove World-oriented behavior metrics from the primary Embodiment UI.

No new causal subsystem.

---

# 40. Recommended third milestone

### Milestone EW-C — Vision Substrate

Deliver only:

```text
VisualApparatus
opaque visual channels
perceptual topology
deterministic sampling
observer-truth isolation
causal provenance
headless tests
```

No requirement for a polished Vision view until the causal substrate is proven.

---

# 41. Overall implementation judgement

Experience & World Architecture Specification v1 is **implementable without destabilizing the canonical Symbiont architecture**.

The current code has crossed an important threshold:

> the scientific observer is now sufficiently separated from the living causal system that the Lab can be reorganized around development without forcing the organism runtime to become a UI-oriented architecture.

The principal mistake to avoid now is overengineering the refactor.

The target should be achieved by:

```text
preserve causal core
+
formalize Lab execution ontology
+
move existing presentation to correct domains
+
add protected acquisition semantics
+
implement real Vision
+
construct integrated Challenge World
```

rather than by:

```text
new runtime
+
new snapshot system
+
new observer transport
+
parallel state models
```

The correct implementation principle is therefore:

> **Refactor ownership before rewriting mechanisms. Add new mechanism only where capability is genuinely absent — principally Vision and integrated acquired-world structure.**

And the final architecture should preserve the specification's defining distinction:

> **Experience is where Symbiont acquires. World is where Symbiont lives with what it has acquired. Mind is where that history becomes cognition. Archive is how we prove it happened.**
