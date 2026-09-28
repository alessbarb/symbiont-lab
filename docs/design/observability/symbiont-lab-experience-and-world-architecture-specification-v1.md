# Symbiont Lab — Experience & World Architecture Specification v1

**Status:** Architecture specification  
**Scope:** Symbiont Lab, Observatory/Workbench, acquisition experiences, integrated worlds, embodiment, perception, experimental reproducibility and lifecycle  
**Primary principle:** *Experience acquires capability. World integrates capability.*

---

## 0. Executive definition

Symbiont Lab must no longer be organized primarily around technical subsystems such as *Body*, *Mind* or *Physics*, nor around conventional AI tasks.

It must be organized around the developmental history of a persistent organism.

A Symbiont exists independently of any particular body or environment. It may enter controlled **Acquisition Experiences** that expose lawful opportunities from which it can discover new structure. It may later enter a **World**, where previously acquired capabilities operate simultaneously under complete environmental consequences.

The fundamental lifecycle is:

```text
                         SYMBIONT
                            │
                            ▼
                    state / checkpoint X
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       ACQUISITION                    ACQUISITION
       EXPERIENCE                     EXPERIENCE
       Embodiment                       Vision
              │                           │
              └─────────────┬─────────────┘
                            │
                  acquired structure
                            │
                            ▼
                         state X'
                            │
                            ▼
                          WORLD
                   integrated challenge
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
          survives                    body dies
              │                           │
              ▼                           ▼
          state X''              dormant Symbiont
                                          │
                                          ▼
                                    new embodiment
                                          │
                                          ▼
                                  reacquisition /
                                   recalibration
```

This architecture makes a strict distinction between:

1. **what physically exists;**
2. **what reaches the organism through an apparatus;**
3. **what the organism has actually acquired;**
4. **what the human observer knows;**
5. **what the organism can subsequently use in an integrated world.**

---

# 1. Scientific foundation

The architecture is compatible with several established ideas in developmental and embodied robotics without requiring Symbiont to become a conventional reinforcement-learning agent.

Research on **sensorimotor contingencies** emphasizes that sensitivity to relationships between actions and their sensory consequences can support the acquisition of body knowledge, memory, generalization and goal-directed capabilities. This strongly supports treating Embodiment as discovery of lawful action–consequence structure rather than as motor-task training.

Developmental robotics also contains a recurring **“starting small”** principle: early developmental conditions can deliberately restrict complexity so that sensorimotor structure becomes learnable before richer environments are introduced. That maps naturally onto Symbiont's Acquisition Experiences.

Active-perception research similarly argues against perception as passive reception of snapshots: perception depends on actions that alter sensory information and reveal regularities. This supports Vision as an active acquisition domain rather than merely attaching a camera to World.

Work on intrinsic motivation and developmental robotics provides useful evidence that exploration can be organized around novelty, prediction change or competence progress rather than externally specified tasks. Symbiont may use analogous endogenous signals if supported by its architecture, but **the Lab must not turn these quantities into an externally imposed reward function**.

Habitat and AI2-THOR offer a useful experimental lesson independently of their task-oriented assumptions: agent, simulator/environment, episode and benchmark should remain separable, and procedural diversity can be valuable for studying generalization. Symbiont should adopt that experimental discipline without adopting semantic goals such as ObjectNav as its developmental ontology.

Research on safe robot learning also supports distinguishing protected acquisition from deployment conditions where complete physical consequences apply. Symbiont is not defined as an RL system, so those algorithms are not directly imported, but the separation between exploration safety and unrestricted deployment consequences is relevant to Lab architecture.

---

# 2. Fundamental architectural invariants

These are normative. Implementations violating them are architecturally incorrect even when they produce attractive behaviour.

## 2.1 World does not directly teach Symbiont

Forbidden:

```text
World object
    ↓
semantic identity
    ↓
Symbiont
```

Required:

```text
World
    ↓
physical interaction
    ↓
Apparatus
    ↓
opaque signals
    ↓
Symbiont
    ↓
acquired structure
```

---

## 2.2 An Experience isolates a discoverable relationship

An Acquisition Experience deliberately reduces environmental complexity so that a class of regularities can be encountered and acquired.

It does **not** specify the correct internal representation.

```text
Experience
    exposes lawful opportunities

Symbiont
    discovers whatever structure its architecture permits
```

---

## 2.3 World does not isolate relationships

World deliberately combines them.

```text
Experience:
controlled acquisition

World:
integrated consequences
```

A World may contain several challenge regions or situations, but these are parts of **one environment/run**, not separate concurrent worlds.

---

## 2.4 Acquired semantics never originate in observer metadata

The Lab may know:

```text
right_shoulder_pitch
cube_004
red
distance = 1.37 m
world_position = (...)
```

Symbiont may receive only the consequences its apparatus physically transduces.

Observer semantics may be displayed by Observatory but never fed back into cognition.

---

## 2.5 Capability is distinct from externally visible behaviour

A Symbiont can acquire a genuine sensorimotor competence without walking.

It can acquire visual persistence without recognizing an object.

It can acquire spatial structure without constructing Cartesian coordinates.

Therefore externally anthropomorphic behaviour must not be used as the definition of successful development.

---

## 2.6 Acquisition Experiences are non-terminal

An Acquisition Experience may expose:

- uncertainty;
- failure;
- reversible fatigue;
- physical cost;
- instability;
- noisy or degraded sensing;
- difficult control;
- conflicting evidence.

It must not intentionally allow irreversible loss of the current body.

The Lab provides a protected developmental envelope.

---

## 2.7 World provides consequence completeness

World removes that protection.

A body may cease to be viable through the normal simulated consequences of:

```text
physical interaction
+
homeostatic state
+
environmental conditions
+
the organism's actions
```

This is not punishment and is not negative reward.

It is physical consequence.

---

## 2.8 Body death is not automatically Symbiont death

```text
Body viability lost
        ↓
Embodiment terminates
        ↓
Symbiont becomes dormant
        ↓
potential new Body
        ↓
new Embodiment epoch
```

Identity, permitted persistent cognition and organism history remain distinct from the physical body.

---

## 2.9 Observatory is epistemically passive

Observability must not influence organism behaviour merely by being enabled.

Human-readable derivations, geometry, labels and analytics are observer-side only.

The existing principle remains:

```text
Cost(tick | Observer OFF)
≈
Cost(tick | Observer ON)
```

except for tightly bounded transport/measurement overhead that cannot affect organism decisions.

---

# 3. Core ontology

## 3.1 Symbiont

Persistent digital organism.

Owns:

```text
identity
genome
germline state
cognition
acquired structure
memory
developmental history
```

Does not intrinsically own a particular body.

---

## 3.2 Body

Physical substrate.

Owns:

```text
physical morphology
dynamics
joints / mechanisms
receptors
effectors
physical health
energy / resources
damage state
```

A Body is not a Symbiont.

---

## 3.3 Embodiment

Current binding:

```text
Symbiont + Body + apparatus bindings
```

An Embodiment has an epoch:

```text
embodiment_epoch
```

A new body means a new epoch.

---

## 3.4 Apparatus

Physical interface transforming reality into organism-accessible signals or organism outputs into physical interventions.

Examples:

```text
motor apparatus
proprioceptive apparatus
interoceptive apparatus
visual apparatus
future auditory apparatus
```

Apparatus structure may be genetically/developmentally provided where physically necessary.

World semantics may not be.

---

## 3.5 Signal

Opaque value/event made available to Symbiont.

Example:

```text
signal.02817
```

not:

```text
left_knee_angle
red_cube_visible
```

Observer metadata may maintain such correspondences separately.

---

## 3.6 Acquisition Experience

Protected experimental domain intended to expose a family of discoverable regularities.

Current initial classes:

```text
Embodiment Experience
Vision Experience
```

Future candidates:

```text
Audition
Abstract
Social
other sensory/developmental domains
```

An Experience is not necessarily a UI view. It is an experimental/runtime concept.

---

## 3.7 Acquired Structure

Any internal structure supported by organism-generated evidence:

```text
relations
predictors
source candidates
competences
persistence hypotheses
uncertainty
concepts
memory
```

---

## 3.8 Capability

Reusable acquired organization that changes what the organism can predict, discriminate, control or integrate.

Capabilities need not have human semantic names.

Examples:

```text
competence.017
visual-capability.008
relation-family.143
```

---

## 3.9 World

Integrated environment in which multiple already available modalities and capabilities operate simultaneously.

World is neither a trainer nor a single benchmark score.

It is the environment in which developmental acquisitions encounter full interactions.

---

## 3.10 Run

One execution from a precise starting state.

```text
Run
├── organism checkpoint
├── run kind
├── configuration
├── environment
├── random seed(s)
├── start conditions
├── resulting causal history
└── resulting organism state
```

A run is immutable historical evidence once completed.

---

# 4. State-X execution model

Every meaningful experiment must start from an explicit organism state.

Define:

```text
X = complete reproducible organism checkpoint
```

A conceptual manifest should include at least:

```text
organism_id
organism_state_hash
genome_id / genome state
tick / developmental age
cognitive state reference
memory state reference
embodiment_epoch
body_id if embodied
apparatus contract
acquired capability manifest
causal provenance head
runtime/schema versions
```

A run therefore becomes:

```text
R = execute(X, Environment, Config, Seed)
```

producing:

```text
X' + causal_record
```

This permits:

```text
same X
├── World(seed 101)
├── World(seed 127)
└── World(seed 149)
```

and:

```text
X_before_vision
        ↓
same World
        ↑
X_after_vision
```

without confusing developmental state with environmental variation.

---

# 5. Acquisition Experience contract

Every Acquisition Experience follows a common abstract contract.

```text
Experience
├── experience_id
├── experience_type
├── starting_checkpoint
├── apparatus requirements
├── protected environment
├── configuration
├── seeds
├── opportunities
├── observations
├── interventions
├── causal evidence
├── acquired changes
├── safety envelope
└── resulting checkpoint
```

It must answer:

```text
What regularities were available?

What could Symbiont physically sense?

What could Symbiont physically change?

What did it actually acquire?

What remains uncertain?

What changed relative to X?
```

It must not encode:

```text
the answer
target semantic concept
required trajectory
desired action
reward for human-defined success
```

---

# 6. Embodiment Experience

## 6.1 Purpose

Embodiment exists to expose the causal structure relating:

```text
effector activity
      ↕
body transformation
      ↕
proprioceptive consequences
      ↕
contact consequences
      ↕
interoceptive consequences
```

Its core question is:

> What can this organism discover about acting through this body?

---

## 6.2 Embodiment is not movement-in-world

Embodiment must not be judged through:

```text
distance travelled
destination reached
resource approached
room navigated
obstacle crossed
```

Those are World-level phenomena.

The current `Body` view's `In World`, environment interaction, resource progress and locomotion-oriented presentation therefore do not belong to the new Embodiment Experience.

---

## 6.3 Protected physical nursery

Embodiment requires enough physics to expose genuine lawful consequences:

```text
gravity
mass
inertia
joint constraints
support
friction
contact
self-contact
actuation cost
interoceptive changes
```

but does not require a semantic environment.

The nursery exists to provide opportunities, not answers.

---

## 6.4 Body viability

During Embodiment:

```text
body death = forbidden terminal outcome
```

The Lab may reset/support/recover physical state if necessary.

These interventions must:

1. remain unavailable as semantic signals to Symbiont;
2. be recorded in observer provenance;
3. never fabricate evidence that the organism interprets as self-caused.

---

## 6.5 Acquired body structure

Potentially observable acquisitions include:

```text
effector → consequence relations
receptor covariation
controllability
repeatability
body boundaries
sensorimotor groups
stable transformations
interoceptive regularities
competences
```

Nothing requires an anatomical representation.

---

## 6.6 Motor Discovery terminology

User-facing `Motor Learning` should be retired.

Preferred ontology:

```text
Action Discovery
Sensorimotor Discovery
Competence
Controllability
```

Example:

```text
effector.14
      ↓
transformation.81
      ↓
signals {31,42,77}
      ↓
prediction
      ↓
causal evidence
      ↓
competence.07
```

---

## 6.7 Acquired Self

The existing Self-Model/Self-View work should evolve into **Acquired Self**.

It represents what can be justified from Symbiont's acquired evidence.

The physical body and acquired structure must remain distinguishable:

```text
APPARATUS TRUTH
≠
ACQUIRED SELF
```

Observer projection may map acquired structure onto physical morphology, but that mapping must be labelled as observer correspondence.

---

## 6.8 Re-embodiment

A new body starts a new embodiment epoch.

Relevant classifications:

```text
retained
transferred
candidate transfer
stale
invalidated
reacquired
novel
```

A new body does not imply a new organism.

After a World body loss:

```text
World
  ↓
body non-viable
  ↓
Symbiont dormant
  ↓
bind new Body
  ↓
new Embodiment Experience
  ↓
reacclimation / discovery
```

---

# 7. Vision Experience

## 7.1 Purpose

Vision exposes lawful regularities in visual sensory change.

Its core question:

> What structure can Symbiont acquire from the temporal behaviour of a visual apparatus?

Vision is not object recognition and is not a first-person World camera UI.

---

## 7.2 Visual apparatus

Initial architecture:

```text
VisualApparatus
├── one or more receptor arrays
├── physical orientation
├── field geometry
├── sampling cadence
├── channel properties
├── apparatus health
└── opaque signal mapping
```

It must not assume human eyes as an architectural invariant.

---

## 7.3 Start small

Initial receptor surfaces should deliberately remain modest.

Possible first experimental configuration:

```text
16×16
or
32×32
```

rather than high-resolution RGB.

The exact dimensions must be experimentally justified.

The objective is to determine the minimum apparatus supporting acquisition of structure, not to maximize image fidelity.

---

## 7.4 Apparatus topology

Physical adjacency of visual receptors may be an innate property of the apparatus.

That means:

```text
receptor topology
= physically available structure
```

while:

```text
grouping into external sources
= acquired structure
```

The Lab may provide the first.

It must not provide the second.

---

## 7.5 Visual acquisition progression

Potential dimensions:

```text
responsiveness
temporal continuity
local coherence
transformation regularity
source differentiation
persistence
occlusion tolerance
self-caused transformation
independent change
cross-field correspondence
uncertainty calibration
```

These are observer-side scientific dimensions, not goals communicated to Symbiont.

---

## 7.6 Visual source candidates

Vision should initially avoid the concept `object`.

Prefer:

```text
cluster
source candidate
coherent source
persistent source
```

Example:

```text
source.17

temporal coherence
persistence
transformations
uncertainty
```

Only evidence may justify consolidation.

---

## 7.7 Active vision

Vision may use movements available through Embodiment to change visual input.

The important relation is not pre-specified:

```text
action
     ↓
visual transformation
```

It must be discovered.

This allows emergence of a distinction between:

```text
self-caused visual change
```

and:

```text
change not explained by current self-action model
```

Active perception research supports treating such action-dependent regularities as central rather than treating perception as passive frame processing.

---

## 7.8 Occlusion and persistence

A controlled Vision Experience may physically generate:

```text
appearance
partial occlusion
absence
reappearance
```

without telling Symbiont that a single object persisted.

Scientific question:

```text
Does acquired structure survive temporary sensory absence?
```

---

## 7.9 Binocular or multi-field perception

Multiple visual arrays may later be supported.

Do not supply:

```text
depth
distance
stereo correspondence
```

as semantics.

Provide independent physical receptor surfaces.

Relations between them must be discovered.

---

## 7.10 Visual Experience safety

Like Embodiment, Vision is an Acquisition Experience.

The visual apparatus/body cannot be irreversibly lost as an intended consequence of the Experience.

---

# 8. Future Acquisition Experiences

The abstraction must support future domains without redesigning Lab.

Candidate examples:

```text
Audition
Touch — if eventually rich enough to justify separation
Social
Abstract
other sensory modalities
```

Each must follow the same grammar:

```text
Apparatus / substrate
        ↓
signals
        ↓
discoverable regularities
        ↓
evidence
        ↓
acquired structure
        ↓
reusable capability
```

An Abstract Experience need not necessarily use the physical body, but it must still respect the prohibition against injecting the desired semantic solution.

---

# 9. World

## 9.1 Purpose

World is the integrated challenge environment.

Its core question:

> What happens when this particular developmental state has to use its acquired capabilities together under complete environmental consequences?

World is therefore closer to a **scientific yincana** than to a training arena.

---

# 10. One World run, not all worlds simultaneously

Default execution:

```text
checkpoint X
    ↓
World configuration W
    ↓
seed S
    ↓
one World run
    ↓
checkpoint X'
```

A World may contain several challenge regions and changing situations.

That does **not** mean multiple independent worlds are active simultaneously.

Concurrent worlds may later be investigated as a specific experiment, but they are not part of the base architecture.

---

# 11. World as yincana

A World can contain sequences or regions that expose combinations such as:

```text
variable support
occlusion
independent movement
conflicting sensory evidence
narrow geometry
novel surfaces
changing illumination
unexpected contact
novel combinations
```

The Lab knows why each region exists.

Symbiont does not receive those purposes.

Example:

```text
Observer protocol:

zone 03
scientific intent:
test persistence during temporary visual loss

Symbiont receives:
ordinary physical/sensory consequences

Symbiont does NOT receive:
"remember this object"
"find the hidden thing"
```

---

# 12. World need not be linear

A yincana is a useful conceptual analogy, not necessarily:

```text
A → B → C → Finish
```

The preferable structure may be:

```text
                    variable terrain
                         │
                   ┌─────┤
                   │     └──── occlusion
                   │
entry ─────────────┼──────── dynamic sources
                   │
                   └──────── constrained geometry
```

Symbiont's own dynamics influence which situations it encounters and how.

This preserves agency.

---

# 13. World families

At least two broad families should eventually be supported.

## 13.1 Challenge World

Highly reproducible experimental environment.

Purpose:

```text
generalization
integration
failure analysis
capability interactions
```

## 13.2 Open World

Less curated environment.

Purpose:

```text
open-ended interaction
novel combinations
long-duration development
```

These are environment/run types, not necessarily separate UI screens.

---

# 14. World consequence completeness

Unlike Acquisition Experiences:

```text
body survival is not guaranteed
```

The Lab does not rescue the body merely because a consequence is undesirable.

Possible chain:

```text
environmental state
        ↓
physical consequence
        ↓
homeostatic deterioration
        ↓
loss of body viability
```

This must not be represented as reward/punishment.

It is simply the simulated physics/homeostasis contract.

---

# 15. World does not erase development

Failure in World may reveal that a previously acquired capability does not generalize.

Example:

```text
competence.17
ROBUST in Embodiment

        ↓

World:
different physical condition

        ↓

predicted consequence fails

        ↓

competence revision / contextualization
```

Therefore:

```text
Experience → capability → World
                        ↓
                 discrepancy
                        ↓
                  refinement
```

An Experience is not a school level permanently completed.

---

# 16. Multimodal integration

World is where modality-specific acquisitions can become evidence about common external structure.

Example:

```text
Vision
cluster.31 ──────┐
                 │
Embodiment       │
contact.07 ──────┼──► source.18
                 │
Action           │
competence.04 ───┤
                 │
Prediction ──────┘
```

The Lab must never assert the common source merely because it knows the physical object generating all signals.

Symbiont must establish the relation.

---

# 17. Acquired World

Use the term:

**Acquired World**

rather than treating `Known World` as binary truth.

It may contain:

```text
supported
tentative
uncertain
stale
contradicted
hypothesized
```

structures.

The screen `World` visualizes interaction.

`Acquired World` is the organism's evidence-supported model.

---

# 18. Spatial structure

Do not require Cartesian coordinates as the first internal spatial representation.

Accept useful structures such as:

```text
topological relations
relative transformations
near/far-like relations
ordering
persistent adjacency
action-dependent relations
```

if those are what Symbiont genuinely acquires.

Observer-side geometry remains available for validation.

---

# 19. Predictions and discrepancies

World should make prediction error particularly visible.

```text
prediction
    ↓
observation
    ↓
match / discrepancy
    ↓
revision
```

Examples:

```text
source expected but absent
contact without known source
unexpected visual motion
competence consequence differs
persistent relation breaks
```

Discrepancies are evidence, not automatic punishment.

---

# 20. Body death and re-embodiment

World is the domain in which irreversible body loss may occur.

Afterward:

```text
WORLD
body e3 no longer viable
        ↓
close embodiment epoch e3
        ↓
record terminal body state
        ↓
Symbiont → dormant
        ↓
new body selected/provided
        ↓
open embodiment epoch e4
        ↓
Embodiment Experience
        ↓
reacquisition / transfer evaluation
```

The new body is not silently substituted mid-World.

This boundary must remain visible in causal history.

---

# 21. Mind

Mind is not another Experience.

Mind is a transversal view over cognition.

It answers:

> What cognitive structure exists, what is active, and how is it changing?

Mind owns presentation of:

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

It does not own:

```text
sensory apparatus
motor discovery
body physiology
world truth
```

---

# 22. Home

Home answers:

> Who is the current Symbiont and what developmental state is it in?

It should show:

```text
organism identity
lifecycle
current state/checkpoint
current embodiment epoch
current body
available/acquired capabilities
recent developmental change
current execution
```

It should launch:

```text
Experience run
or
World run
```

from an explicit state.

---

# 23. Archive

Archive becomes the persistent scientific developmental record.

It should contain:

```text
Symbiont lineage
checkpoints
Embodiment epochs
Experience runs
World runs
body deaths
re-embodiments
capability acquisition
capability revisions
causal histories
experimental configurations
seeds
comparisons
```

Archive is not merely “previous runs”.

It answers:

> How did this organism become its current state?

---

# 24. New navigation

Recommended information architecture:

```text
HOME

MIND

EXPERIENCES
├── EMBODIMENT
├── VISION
└── future domains

WORLD

ARCHIVE
```

Whether `EXPERIENCES` is a visible group label or only an architectural grouping may be decided during UI implementation.

`Lab/Experiments` disappears as a top-level organism-facing view.

The Lab continues to exist as infrastructure.

---

# 25. Experience UI grammar

All Acquisition Experience views should share a visual grammar.

```text
┌───────────────────────────────────────────────────┐
│ EXPERIENCE                                        │
├──────────────────┬────────────────────────────────┤
│ APPARATUS        │ ACQUIRED STRUCTURE             │
├──────────────────┴────────────────────────────────┤
│ ACTIVE DISCOVERY                                  │
│ signal → relation → prediction → evidence         │
├──────────────────────┬────────────────────────────┤
│ CAPABILITIES         │ UNRESOLVED / CONTRADICTED │
├──────────────────────┴────────────────────────────┤
│ RECENT DEVELOPMENT                                │
└───────────────────────────────────────────────────┘
```

Possible modes:

```text
Discovery
Apparatus
Acquired
```

The dominant view is `Discovery`, not physical spectacle.

---

# 26. Embodiment UI

Primary visualization:

```text
apparatus topology
+
active causal discovery
+
acquired body correspondence
```

Do not show:

```text
room
world trajectory
resource
destination
navigation
```

The body 3D representation remains valuable but becomes a scientific apparatus map.

---

# 27. Vision UI

Primary visualization:

```text
visual receptor field
+
visual transformations
+
source candidates
+
persistence
+
prediction/evidence
```

Do not make a conventional RGB POV camera the conceptual centre.

If a ground-truth image is useful for researchers, it belongs behind an explicit observer-only layer.

---

# 28. World UI

World deliberately uses a different grammar.

Primary modes:

```text
Acquired
Compare
Observer Truth
```

### Acquired

What Symbiont currently represents.

### Compare

Acquired structure versus physical truth.

### Observer Truth

Complete physical scene, explicitly labelled unavailable to Symbiont.

The World screen may legitimately display:

```text
body position
movement
trajectory
environment
contacts
objects
challenge regions
```

because here spatial behaviour is part of integrated interaction.

---

# 29. Shared global inspector

Every major observable entity should use one inspector architecture:

```text
receptor
signal
relation
concept
predictor
competence
visual source
world source
body region
```

The inspector displays:

```text
identity
state
age
confidence/uncertainty
evidence
relations
causal provenance
cross-domain links
```

Examples:

```text
Open in Mind
Open in Embodiment
Open in Vision
Open in World
```

Navigation preserves selected entity/provenance context.

---

# 30. Observer Truth

Every domain obeys:

```text
SYMBIONT EVIDENCE
≠
OBSERVER TRUTH
```

Observer annotations should be globally switchable and unmistakably marked.

Examples:

```text
Symbiont:
source.17

Observer annotation:
corresponds strongly with physics entity cube_004
```

The annotation must never become an input to the organism.

---

# 31. Experimental reproducibility

Every run must persist:

```text
run_id
run_kind
organism_id
starting_checkpoint
ending_checkpoint
body / embodiment epoch
environment definition/version
apparatus definition/version
all relevant seeds
physics version
runtime version
experiment configuration
interventions/resets
causal trace
termination reason
```

A result without enough information to reproduce its initial condition is scientifically incomplete.

---

# 32. Causal provenance

Required causal chain:

```text
physical event
    ↓
apparatus state
    ↓
receptor sample
    ↓
opaque signal
    ↓
cognitive evidence
    ↓
acquired relation
    ↓
prediction / competence / source
    ↓
future consequence
```

Restore/replay must preserve not only final causal state but enough causal history to reconstruct why the state exists.

---

# 33. Metrics philosophy

No single reward or overall score is normative.

## Embodiment metrics

Prefer:

```text
causal relations acquired
repeatability
prediction improvement
stable mappings
competences
competence maturity
unresolved channels
calibrated uncertainty
transfer across embodiment epochs
```

Avoid making primary:

```text
distance
speed
walking
task completion
```

---

## Vision metrics

Prefer:

```text
predictive utility
temporal coherence
source stability
persistence evidence
occlusion recovery
transformation predictability
self-caused/external discrimination
generalization
uncertainty calibration
```

Avoid making primary:

```text
semantic classification accuracy
object labels
human-defined recognition tasks
```

---

## World metrics

Prefer:

```text
capabilities recruited
cross-modal integration
prediction validity
discrepancies
model revisions
unexplained observations
novel acquired structure
generalization
recovery after surprise
stale structures
causal attribution quality
```

Behavioural measurements such as displacement remain observer descriptors, not developmental objectives.

---

# 34. Evaluation by ablation

Whenever practical, capability claims should be tested through controlled comparisons.

Examples:

```text
X before Vision
vs
X after Vision
on the same World seeds
```

```text
normal plasticity
vs
plasticity disabled
```

```text
acquired competence available
vs
competence withheld from execution
```

This allows claims about actual causal usefulness rather than merely correlated maturation.

---

# 35. Generalization gates

A capability should not be described as broadly acquired merely because it succeeds in its nursery.

Suggested evidence classes:

```text
ACQUIRED
works inside acquisition conditions

TRANSFERRED
works under a changed acquisition configuration

GENERALIZED
contributes usefully in World conditions not used to establish it

ROBUST
survives repeated perturbations / seeds with predefined evidence criteria
```

Exact names can align with existing competence maturity contracts where appropriate.

---

# 36. Protected acquisition must not become hidden training

The Lab may:

```text
restrict complexity
ensure body survival
provide controlled physical variability
reset observer-defined environment state
vary stimulus conditions
```

It must not:

```text
choose the correct action
reinforce a semantic answer
inject target labels
silently reward desired behaviour
change evidence because researchers prefer an outcome
```

The distinction is:

```text
curriculum of opportunities
≠
curriculum of answers
```

This is where developmental-robotics “starting small” is useful to Symbiont, while conventional task curricula must be treated cautiously.

---

# 37. Intrinsic exploration

Symbiont may eventually select what to explore based on endogenous signals such as:

```text
uncertainty
novelty
prediction improvement
competence progress
surprise
```

Research on intrinsic motivation provides precedent for learning-progress and prediction-based exploration.

However:

```text
observer metric
≠
intrinsic drive automatically
```

No Lab metric should silently become motivation.

Any intrinsic mechanism must be explicit in Symbiont architecture and causally traceable.

---

# 38. World design principles

A useful World challenge should vary along independent axes.

Examples:

```text
physical dynamics
visual conditions
occlusion
terrain/support
source motion
novelty
multimodal consistency
resource availability
homeostatic pressure
apparatus degradation
```

World generation should support deterministic seeds.

Procedural environment generation in embodied-AI platforms demonstrates the value of large, diverse environment distributions for testing transfer and zero-shot generalization; Symbiont can borrow the principle while avoiding semantic task labels.

---

# 39. Challenge manifests

Each yincana/world may have an observer-only manifest.

Example:

```yaml
world_id: integrated-world-v1
seed: 127

situations:
  - id: support_variation
    observer_purpose:
      - sensorimotor generalization

  - id: temporary_occlusion
    observer_purpose:
      - visual persistence

  - id: independent_source_motion
    observer_purpose:
      - self/external differentiation

  - id: multimodal_contact
    observer_purpose:
      - visual-contact integration
```

This manifest must never become the organism's task list.

---

# 40. Termination

Every run has an explicit termination reason.

Acquisition examples:

```text
time_budget_reached
evidence_window_complete
operator_stop
experimental_condition_complete
protected_recovery
technical_failure
```

World examples additionally include:

```text
body_non_viable
world_duration_complete
operator_stop
technical_failure
```

Never encode:

```text
won
lost
```

as the fundamental lifecycle model.

---

# 41. Current-code refactoring consequences

Based on current `main`, the existing Body/Mind separation should be reorganized.

## Move from Body to World

```text
body/world-view.js
body/world-state.js

In World
world geometry
external entities
global trajectory
resource-distance presentation
environment interactions
```

---

## Retain/refactor into Embodiment

```text
body/anatomical-visual.js
body/model.js
body/self-model.js
body/self-view.js
relevant morphology-neutral viewer infrastructure
```

with conceptual replacement:

```text
Body
→
Embodiment Experience
```

---

## Move from Mind to Embodiment

```text
motor-learning.js
motor-learning-model.js
motor-learning-chart.js
motor-learning-history.js
```

after renaming/reframing around:

```text
Action Discovery
Sensorimotor Discovery
Competence
```

---

## Split current identity-sensory responsibilities

```text
organism identity
→ Home

body schema / phenotype correspondence
→ Embodiment

proprioceptive/interoceptive apparatus
→ Embodiment

future visual apparatus
→ Vision

cognitive use of signals
→ Mind
```

---

## Remove Lab/Experiments from primary navigation

The functionality must first be inventoried and reassigned.

The runtime concept of experiments/studies remains valid.

The user-facing organism ontology does not require a generic `Lab` screen.

---

# 42. New runtime abstractions

Recommended conceptual interfaces:

```text
ExperienceDefinition
ExperienceRun
ExperienceSnapshot

WorldDefinition
WorldRun
WorldSnapshot

ApparatusDefinition
ApparatusBinding

AcquiredCapability
CapabilityEvidence

OrganismCheckpoint
EmbodimentEpoch

ObserverTruth
CausalProvenance
```

The exact implementation language/classes may differ. The conceptual boundaries must remain.

---

# 43. Snapshot contract

Future observer snapshots should explicitly separate:

```text
truth
apparatus
organism_evidence
acquired_structure
observer_correspondence
```

Never publish a single flattened representation in which it becomes impossible to tell whether a relation originated from:

```text
Physics
Symbiont
or
Observatory derivation
```

---

# 44. Experience/World state machine

Recommended lifecycle:

```text
CHECKPOINT_AVAILABLE
        │
        ▼
RUN_PREPARING
        │
        ▼
RUNNING
        │
        ├──► PAUSED / operator
        │
        ├──► PROTECTED_RECOVERY   acquisition only
        │
        ▼
RUN_COMPLETE
        │
        ▼
CHECKPOINT_AVAILABLE
```

World body loss:

```text
RUNNING
   ↓
BODY_NON_VIABLE
   ↓
EMBODIMENT_EPOCH_CLOSED
   ↓
SYMBIONT_DORMANT
```

A later body assignment creates a new epoch.

---

# 45. Scientific anti-patterns

The following should be explicitly prohibited.

### Semantic leakage

```text
physics entity ID → cognition
```

### Observer leakage

```text
observer classification → acquired source
```

### Goal leakage

```text
researcher's desired outcome → action selection
```

### Evaluation leakage

```text
benchmark metric → hidden reward
```

### View leakage

```text
opening Observatory changes organism computation
```

### Experience leakage

```text
Vision directly receives World object identities
```

### Mortality leakage

```text
Embodiment nursery accidentally becomes survival World
```

### World protection leakage

```text
Lab repeatedly rescues body in World to preserve a preferred run
```

---

# 46. Initial implementation order

## Phase A — Architectural boundaries

1. Formalize `Experience` vs `World`.
2. Introduce explicit run kind.
3. Formalize state-X/checkpoint manifests.
4. Formalize acquisition safety vs World consequence completeness.
5. Formalize observer-truth separation.
6. Document body-death/re-embodiment lifecycle.

No large UI changes should precede these contracts.

---

## Phase B — Embodiment extraction

1. Rename conceptual Body view to Embodiment.
2. Remove `In World`.
3. Extract `world-view.js` and `world-state.js`.
4. Move motor-learning presentation from Mind.
5. Reframe Motor Learning → Action/Sensorimotor Discovery.
6. Rework Self-Model → Acquired Self.
7. Implement Experience-standard layout.
8. Remove navigation-oriented metrics from primary presentation.
9. Add protected-acquisition lifecycle.

---

## Phase C — Vision substrate

1. Define `VisualApparatus`.
2. Define receptor topology contract.
3. Implement low-resolution physical sampling.
4. Deliver only opaque signals.
5. Add reproducible visual nursery.
6. Establish ground-truth observer channel separately.
7. Instrument causal path:
   `stimulus → receptor → signal → cognition`.
8. Only then implement Vision UI.

The UI must not precede the actual apparatus.

---

## Phase D — Vision acquisition

Investigate progressively:

```text
temporal response
coherence
transformations
persistence
occlusion
self-caused change
independent change
```

Each claim requires predictive/generalization evidence.

---

## Phase E — World extraction

1. Move old `Body/In World` functionality.
2. Build World as integrated scene.
3. Add `Acquired / Compare / Observer Truth`.
4. Integrate provenance from Embodiment/Vision/Mind.
5. Define first reproducible yincana.
6. Allow complete body consequences.
7. Wire body loss → dormant Symbiont.
8. Preserve complete run provenance.

---

## Phase F — First integrated experiment

Suggested design:

```text
X0
│
├── Embodiment E1
│       ↓
│      X1
│
├── Vision V1
│       ↓
│      X2
│
└── World W1
        ↓
       X3
```

Then compare:

```text
X0 → W1
X1 → W1
X2 → W1
```

using matched World seeds.

This directly tests whether each Acquisition Experience produces capabilities with causal utility outside its nursery.

---

# 47. First World yincana

The first World should remain small enough to interpret scientifically.

Suggested physical features:

```text
stable starting region
variable support region
simple obstruction
temporary visual occlusion
independently changing visual source
contact opportunity
novel combined region
```

It should not include semantic tasks.

Observer hypotheses:

```text
Does Embodiment acquisition improve action predictability?

Does Vision acquisition improve persistence under occlusion?

Can self-caused and independent change be distinguished?

Do visual and contact evidence converge?

Does a nursery-robust competence generalize?

How does Symbiont react when an acquired relation fails?
```

---

# 48. First release gates

Architecture is not considered complete merely because screens render.

### Gate A — epistemic isolation

No forbidden World/observer semantics reach Symbiont.

### Gate B — causal trace

At least one complete path is inspectable:

```text
physical event
→ apparatus
→ receptor
→ signal
→ evidence
→ acquired structure
```

### Gate C — Embodiment acquisition

At least one sensorimotor relation is acquired and demonstrably predictive.

### Gate D — Vision acquisition

At least one visual relation is acquired and demonstrably predictive without semantic labels.

### Gate E — transfer

An acquisition improves or changes behaviour/prediction under a held-out condition.

### Gate F — World integration

At least two independently acquired domains contribute evidence during a World run.

### Gate G — consequence lifecycle

A World body-loss event correctly closes the body epoch and leaves the Symbiont dormant/re-embodiable.

### Gate H — replay

A run can be reproduced from its recorded state/configuration/seed within the project's declared determinism guarantees.

---

# 49. Overall product model

The redesigned Lab becomes:

```text
HOME
Who is this organism and where is it developmentally?

MIND
What cognitive structure exists and changes?

EXPERIENCES
Where are new capabilities acquired?

    EMBODIMENT
    What happens when I act through this body?

    VISION
    What structure exists in visual change?

    ...

WORLD
What happens when everything acquired must coexist
under integrated environmental consequences?

ARCHIVE
How did this organism become what it is?
```

---

# 50. Final architectural principle

The redesigned laboratory should make it impossible to confuse:

```text
learning about the body
with
moving through a world

learning to structure vision
with
looking at a rendered scene

acquiring a capability
with
passing a task

observer knowledge
with
organism knowledge

body death
with
organism death

an acquisition nursery
with
life in the world
```

The intended developmental architecture is:

```text
                  ┌───────────────┐
                  │   SYMBIONT    │
                  └───────┬───────┘
                          │
                 persistent identity
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       EMBODIMENT                    VISION
       EXPERIENCE                    EXPERIENCE
             │                         │
       action/body               visual structure
        discovery                  discovery
             │                         │
             └────────────┬────────────┘
                          │
                          ▼
                         MIND
                integrates cognition
                          │
                          ▼
                         WORLD
                  integrated reality
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
             survives          body lost
                │                   │
                │                   ▼
                │              DORMANT
                │                   │
                │                   ▼
                │             NEW BODY
                │                   │
                └──────────────┬────┘
                               ▼
                        further development
```

The shortest statement of the architecture is therefore:

> **Experience is where Symbiont acquires. World is where Symbiont lives with what it has acquired. Mind is where that history becomes cognition. Archive is how we prove it happened.**
