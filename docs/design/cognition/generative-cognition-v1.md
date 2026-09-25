# Generative Cognition v1 — Canonical Specification

**Status:** proposed — ready to freeze  
**Target status:** canonical  
**Version:** 1.1 final candidate  
**Domain:** cognition  
**Scope:** `symbiont` core + minimal integration with Runtime v2, Memory, Agency, Embodiment, Structural Plasticity and Observatory  
**Primary objective:** autonomous, bounded, epistemically isolated non-factual cognition  
**Depends on:** Runtime v2, CognitiveGraph, Episodic Experience Memory, Private SLM, Prospective Agency, Embodiment v2, structural plasticity  
**Supersedes:** no existing canonical subsystem  
**Language:** English

---

# 1. Purpose

Generative Cognition v1 introduces a complete substrate through which a Symbiont can autonomously determine what unresolved internal structure deserves cognitive processing, construct and manipulate possible non-factual experience, compare alternatives, derive hypotheses, test those hypotheses against later reality and allow repeated cognitive use to influence structural organisation without converting imagination into factual knowledge.

The canonical objective is:

> **Allow a Symbiont to autonomously select, construct, manipulate, compare, test and safely consolidate bounded non-factual possible experience while preserving strict separation between generated cognition and factual knowledge.**

The significant terms are:

```text
autonomously select
construct
manipulate
compare
test
consolidate

non-factual
bounded
```

---

# 2. Canonical principles

Three constitutional principles govern the complete domain.

## 2.1 Reality authority

```text
REALITY MAY CORRECT IMAGINATION

IMAGINATION MAY PROPOSE REALITY

IMAGINATION MUST NEVER DECLARE REALITY
```

## 2.2 Endogenous thought selection

```text
THE ORGANISM MAY CHOOSE
WHAT TO THINK ABOUT

THE LABORATORY MUST NOT CHOOSE
WHAT THE ORGANISM THINKS ABOUT
```

## 2.3 Cognitive consolidation

```text
THINKING MAY CHANGE
HOW THE ORGANISM THINKS

THINKING ALONE MAY NOT CHANGE
WHAT THE ORGANISM KNOWS TO BE FACTUAL
```

---

# 3. Definition

**Generative Cognition** is the Symbiont-owned cognitive domain through which the organism:

```text
detects unresolved internal structure
        ↓
selects a cognitive target
        ↓
constructs possible states
        ↓
develops alternative trajectories
        ↓
compares predictions and hypotheses
        ↓
may propose a real test
        ↓
reconciles prediction with later observation
        ↓
learns from reality
        ↓
consolidates recurrent cognitive demand
```

Generative Cognition therefore includes:

```text
endogenous agenda formation

prediction
multi-step rollout
branching

episodic replay
counterfactual generation
recombination

hypothesis formation
hypothesis comparison

epistemic-value estimation

reconciliation with later reality

generative consolidation
```

---

# 4. Explicit non-goals

Generative Cognition v1 does not implement:

```text
general abstraction
analogy
mathematics
language

sleep physiology
dream phenomenology

social-specific imagination

environment implementations

general goal reasoning

recursive self-model simulation

human-like consciousness
```

Those capabilities may later use Generative Cognition.

They must not become part of its v1 implementation.

---

# 5. Architectural closure

Generative Cognition v1 closes the architecture for:

```text
Generative Cognitive Workspace

multi-step imagination

offline cognition substrate

composition of world models

prospective-agency integration

memory → prediction → imagination

generative observability

endogenous thought selection

generative consolidation
```

No additional architecture specification is required for those capabilities.

Remaining work is:

```text
implementation
verification
falsification
scientific validation
```

---

# 6. Canonical ownership

The complete separation of responsibilities is:

```text
GenerativeAgenda
    owns WHAT unresolved structure
    is eligible for thought


GenerativeScheduler
    owns WHEN computation
    may occur


GenerativeWorkspace
    owns HOW temporary
    generative cognition unfolds


GenerativeModels
    own learned predictive capabilities


GenerativeHypothesis
    owns persistent non-factual propositions


GenerativeReconciliation
    owns comparison with later reality


GenerativeConsolidation
    owns evidence about recurrent cognitive use


StructuralPlasticity
    owns durable cognitive structure


ProspectiveAgency
    owns action selection


Embodiment
    owns current Body execution authority


Reality
    owns new external factual evidence
```

No subsystem may absorb another's authority.

---

# 7. Architectural position

Generative Cognition belongs to:

```text
Symbiont
```

It does not belong to:

```text
Body
EmbodimentEpisode
World
Physics3D
symbiont_lab
Observatory
```

Conceptually:

```text
Symbiont
│
├── perception
├── cognition
├── memory
├── models
├── concepts
├── development
├── plasticity
├── agency
│
└── generative cognition
```

---

# 8. Environment independence

Generative Cognition consumes internal representations.

It does not own environments.

Future environments may include:

```text
PhysicalEnvironment
SocialEnvironment
SymbolicEnvironment
AbstractEnvironment
```

but the dependency direction is:

```text
environment
    ↓
experience
    ↓
Symbiont
    ↓
Generative Cognition
```

not:

```text
Generative Cognition
    ↓
owns environment
```

---

# 9. Fundamental epistemic ontology

Every cognitive representation relevant to generation must expose epistemic provenance.

```python
class EpistemicOrigin(Enum):
    OBSERVED = "observed"

    REMEMBERED = "remembered"
    INFERRED = "inferred"

    REPLAYED = "replayed"
    IMAGINED = "imagined"
    COUNTERFACTUAL = "counterfactual"

    ABSTRACT = "abstract"
```

`ABSTRACT` is reserved for future use.

v1 must be structurally compatible with it without implementing abstraction.

---

# 10. OBSERVED

`OBSERVED` means independently grounded factual experience.

Generative Cognition cannot manufacture it.

Only canonical factual pathways may produce new observational support.

---

# 11. REMEMBERED

A remembered state originates from factual episodic history.

But:

```text
remembered event
!=
new factual event
```

Repeated recall cannot increment observation count.

---

# 12. INFERRED

An inferred state results from learned models operating on factual information.

Inference may become highly confident.

It remains distinct from observation.

---

# 13. REPLAYED

Replay reconstructs prior experience for internal processing.

```text
replay
may change cognitive use statistics

replay
must not change factual sample counts
```

---

# 14. IMAGINED

An imagined state represents a possibility that may never have occurred.

It may combine:

```text
memory fragments
model predictions
conceptual relations
candidate actions
```

---

# 15. COUNTERFACTUAL

A counterfactual starts from factual, remembered or inferred structure and changes some internal candidate condition.

Example:

```text
experienced:

S0 + A → S1


counterfactual:

S0 + B → ?
```

---

# 16. ABSTRACT

The representation is reserved for future states that are not tied to one concrete episode.

No `AbstractionEngine` exists in v1.

No placeholder implementation may pretend abstraction exists.

---

# 17. Epistemic authority

Origin and authority are distinct.

```text
OBSERVED
    may create factual support

REMEMBERED
    refers to existing factual support

INFERRED
    hypothesis-level

REPLAYED
    non-factual

IMAGINED
    non-factual

COUNTERFACTUAL
    non-factual

ABSTRACT
    non-factual until independently grounded
```

Hard invariant:

```text
origin != OBSERVED
    =>
cannot create new factual external evidence
```

---

# 18. Two different contamination classes

Generative Cognition must protect against two independent classes of contamination.

## 18.1 Factual contamination

```text
generated cognition
        ↓
factual knowledge
```

without independent observation.

Invariant metric:

```text
factual_contamination_count == 0
```

## 18.2 Agenda contamination

```text
laboratory or hidden world state
        ↓
GenerativeAgenda
```

causing external control over what the organism thinks about.

Invariant metric:

```text
agenda_contamination_count == 0
```

Both are release-blocking.

An organism with:

```text
factual_contamination_count == 0
```

is still not cognitively autonomous if:

```text
agenda_contamination_count > 0
```

---

# 19. EpistemicFirewall

Canonical component:

```text
EpistemicFirewall
```

It rejects:

```text
generated → factual episodic experience

generated → factual causal evidence

generated → BodySchema evidence

generated → execution binding

generated → factual OutcomeValue learning

generated → observed Private SLM sample

generated → factual SignalKnowledge evidence

generated → external world observation
```

---

# 20. No factual promotion API

There must never exist:

```python
generated_state.promote_to_fact()
```

or equivalent.

The only valid path is:

```text
generated prediction
        ↓
possible real action
        ↓
independent observation
        ↓
normal factual evidence path
```

---

# 21. Core package

Canonical implementation target:

```text
src/symbiont/cognition/generative/
```

Recommended structure:

```text
generative/
├── __init__.py
├── types.py

├── epistemic.py

├── state.py
├── transition.py
├── episode.py

├── agenda.py
├── scheduler.py

├── workspace.py

├── model.py
├── registry.py

├── budget.py

├── rollout.py
├── branching.py

├── replay.py
├── counterfactual.py
├── recombination.py

├── hypothesis.py
├── reconciliation.py

├── consolidation.py

├── calibration.py

├── persistence.py
└── projection.py
```

Files may be merged during implementation.

Responsibilities must remain separable.

---

# 22. GenerativeState

Conceptual contract:

```python
@dataclass(frozen=True, slots=True)
class GenerativeState:
    state_id: str
    episode_id: str

    origin: EpistemicOrigin

    parent_state_id: str | None
    depth: int

    features: tuple[GeneratedFeature, ...]
    active_concept_ids: tuple[str, ...]
    relation_refs: tuple[str, ...]

    source_episode_ids: tuple[str, ...]
    source_model_ids: tuple[str, ...]
    source_state_ids: tuple[str, ...]

    uncertainty: float
    coherence: float

    generative_tick: int
```

Mandatory properties:

```text
identity
provenance
episode ownership
parentage
depth
uncertainty
```

---

# 23. Abstraction-ready state representation

`GenerativeState` must not assume:

```text
one state
==
one imagined external scene
```

It must be capable of representing:

```text
concrete state

relation-only state

state composed from several episodes

state not tied to one concrete episode
```

No physical field may be mandatory.

Examples of forbidden universal fields:

```text
position
velocity
body_id
object_id
anatomy
```

Domain models may expose those through generated features where appropriate.

---

# 24. GeneratedFeature

```python
@dataclass(frozen=True, slots=True)
class GeneratedFeature:
    token: str
    value_class: int | float | str | None

    confidence: float

    source_model_id: str | None
```

No human semantic vocabulary belongs to the generic substrate.

---

# 25. GenerativeTransition

```python
@dataclass(frozen=True, slots=True)
class GenerativeTransition:
    transition_id: str
    episode_id: str

    source_state_id: str
    target_state_id: str

    operation: GenerativeOperation
    model_ids: tuple[str, ...]

    uncertainty_before: float
    uncertainty_after: float

    predicted_outcomes: tuple[str, ...]

    generative_tick: int
```

---

# 26. Generative operations

Implemented:

```text
PREDICT

BRANCH

REPLAY

COUNTERFACTUAL

RECOMBINE
```

Reserved:

```text
ABSTRACT

ANALOGIZE

COMPOSE

DECOMPOSE
```

Reserved operations must reject invocation in v1.

---

# 27. GenerativeEpisode

```python
@dataclass(slots=True)
class GenerativeEpisode:
    episode_id: str
    organism_id: str

    target_id: str | None

    root_state_id: str
    mode: GenerativeMode

    started_symbiont_tick: int
    started_generative_tick: int

    source_episode_ids: tuple[str, ...]

    state_count: int
    transition_count: int
    branch_count: int

    max_depth_reached: int

    termination_reason: GenerativeTermination | None
```

A GenerativeEpisode is not an EmbodimentEpisode.

---

# 28. Generative time

Introduce:

```text
generative_tick
```

Canonical distinction:

```text
World time
!=
Body time
!=
Embodiment time
!=
Symbiont time
!=
Generative time
```

A single Symbiont tick may contain several internal transitions.

Generative time cannot advance Body age or external state.

---

# 29. GenerativeAgenda

Canonical component:

```text
GenerativeAgenda
```

Its single responsibility is:

> determine which organism-owned unresolved internal structures are eligible for bounded generative processing.

It answers:

```text
WHAT?
```

It does not answer:

```text
WHEN?
HOW?
WHAT IS TRUE?
WHICH ACTION MUST EXECUTE?
```

---

# 30. GenerativeTarget

```python
@dataclass(frozen=True, slots=True)
class GenerativeTarget:
    target_id: str

    source: AgendaSource
    source_refs: tuple[str, ...]

    created_tick: int

    uncertainty: float
    persistence: float
    recurrence: int

    estimated_resolvability: float | None

    last_selected_tick: int | None
    selection_count: int

    last_progress_tick: int | None
```

A target references unresolved internal state.

It does not contain human-readable goals.

---

# 31. AgendaSource

Initial sources:

```python
class AgendaSource(Enum):
    PREDICTION_ERROR = "prediction_error"

    MODEL_DISAGREEMENT = "model_disagreement"

    ACTIVE_HYPOTHESIS = "active_hypothesis"

    UNCERTAINTY = "uncertainty"

    EPISODIC_INCOMPLETENESS = "episodic_incompleteness"

    PROSPECTIVE_DECISION = "prospective_decision"

    RECURRING_CONFLICT = "recurring_conflict"
```

Additional sources require explicit architectural review.

---

# 32. Agenda constitutional boundary

Every agenda target must have a provenance path:

```text
target
  ↓
source_refs
  ↓
organism-owned internal state
```

Forbidden target origins:

```text
laboratory instruction

task success criterion

hidden simulator state

ground-truth world label

benchmark answer

observer interpretation
```

Any such target increments:

```text
agenda_contamination_count
```

and constitutes a release-blocking failure.

---

# 33. AgendaCandidate

```python
@dataclass(frozen=True, slots=True)
class AgendaCandidate:
    target: GenerativeTarget

    uncertainty_signal: float
    recurrence_signal: float
    conflict_signal: float

    expected_information_gain: float | None
    estimated_resolvability: float | None

    recent_attention: float

    progress_signal: float | None
```

---

# 34. Agenda selection principles

Selection may consider:

```text
unresolved uncertainty

prediction error

model disagreement

persistence

recurrence

expected discriminability

estimated resolvability

recent attention

recent progress
```

No one signal always dominates.

Particularly:

```text
maximum uncertainty
!=
automatic priority
```

because some uncertainty may be irreducible.

---

# 35. Agenda must support stopping

Cognitive autonomy requires more than knowing when to start.

It must also know when to stop.

Expected lifecycle:

```text
new unresolved target
    ↓
agenda entry
    ↓
processing
    ↓

one of:

resolved
stagnant
irreducible
temporarily unproductive
superseded
```

Desired behaviour:

```text
resolved target
    → falls out of agenda

irreducible target
    → loses priority after no progress

stagnant target
    → temporary suppression

newly learnable target
    → may gain priority
```

No laboratory intervention should be required.

---

# 36. Agenda anti-rumination rule

A target that repeatedly produces:

```text
no novel branch

no uncertainty reduction

no useful disagreement change

no hypothesis refinement

no testable consequence

no representational change
```

must lose short-term selection priority.

This is computational resource regulation.

It is not semantic censorship.

---

# 37. Agenda progress

Agenda should maintain a bounded notion of progress.

Possible indicators:

```text
uncertainty reduction

model disagreement reduction

new hypothesis

hypothesis refinement

new discriminating observation candidate

novel valid branch

successful reconciliation
```

Progress must derive only from organism-owned state.

---

# 38. Target retirement

A target may be retired when:

```text
resolved

superseded

permanently invalidated

source structure no longer exists
```

Temporary unproductivity should generally cause suppression, not permanent deletion.

---

# 39. GenerativeScheduler

Scheduler answers:

```text
WHEN?
```

Agenda answers:

```text
WHAT?
```

Workspace answers:

```text
HOW?
```

Canonical flow:

```text
Agenda
    ↓
target

Scheduler
    ↓
opportunity + budget

Workspace
    ↓
episode
```

---

# 40. GenerativeMode

```python
class GenerativeMode(Enum):
    ONLINE = "online"
    IDLE = "idle"
    OFFLINE = "offline"
```

---

# 41. ONLINE mode

Expected uses:

```text
one-step prediction
short prospection
small counterfactual
candidate action comparison
low-depth rollout
```

Real-time interaction retains priority.

---

# 42. IDLE mode

Expected uses:

```text
replay
hypothesis comparison
model disagreement
small recombination
calibration
```

---

# 43. OFFLINE mode

Allows larger bounded internal activity:

```text
deeper replay
longer rollout
larger branching
cross-episode recombination
hypothesis exploration
generative consolidation
```

---

# 44. Offline cognition is not sleep

Canonical invariant:

```text
OFFLINE cognition
!=
sleep physiology
```

Sleep remains a future independent specification.

---

# 45. GenerativeWorkspace

Workspace owns temporary non-factual cognition.

Responsibilities:

```text
active episode

states
transitions
branches

model routing

budget enforcement

deduplication

temporary hypotheses

termination
```

It does not own:

```text
factual memory
factual evidence
CognitiveGraph authority
action execution
```

---

# 46. No monolithic WorldModel

Generative Cognition composes specialised learned models.

It must not introduce an omniscient:

```python
WorldModel
```

Potential contributors include:

```text
Private SLM

SensorimotorDynamicsModel

CompetenceEffectModel

BodySchema constraints

CognitiveGraph learned relations

episodic projections

SignalKnowledge

future social models

future symbolic models
```

---

# 47. GenerativeModel protocol

```python
class GenerativeModel(Protocol):

    @property
    def model_id(self) -> str:
        ...

    def supports(
        self,
        operation: GenerativeOperation,
        state: GenerativeState,
    ) -> bool:
        ...

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        ...
```

A valid model may answer:

```text
I cannot predict this
```

by returning no proposal.

Fabrication is not required.

---

# 48. Initial adapters

v1 should initially adapt:

```text
Private SLM

SensorimotorDynamicsModel

CompetenceEffectModel

Episodic Memory projection
```

No duplicate predictive authority should be created.

---

# 49. GeneratedProposal

```python
@dataclass(frozen=True, slots=True)
class GeneratedProposal:
    features: tuple[GeneratedFeature, ...]

    predicted_outcomes: tuple[str, ...]

    uncertainty: float
    coherence: float

    model_id: str

    support_refs: tuple[str, ...]
```

Support references explain origin.

They are not new factual evidence.

---

# 50. GenerativeModelRegistry

Canonical infrastructure:

```text
GenerativeModelRegistry
```

Responsibilities:

```text
registration

capability discovery

model identity

query routing

availability
```

It owns no factual knowledge and makes no action decisions.

---

# 51. GenerativeBudget

```python
@dataclass(frozen=True, slots=True)
class GenerativeBudget:
    max_states: int
    max_transitions: int

    max_depth: int
    max_branches: int

    max_model_queries: int
```

Runtime may additionally impose:

```text
max_compute_time
```

Technical compute budgets must never masquerade as:

```text
biological energy
motivation
reward
```

---

# 52. Initial engineering limits

Reasonable starting values:

```text
max_depth          = 8

max_branches       = 8

max_states         = 64

max_transitions    = 64

max_model_queries  = 128
```

These are engineering defaults.

Not organism constants.

---

# 53. RolloutEngine

Multi-step generation:

```text
S0
 ↓
S1
 ↓
S2
 ↓
...
 ↓
Sn
```

Each generated state can become input to another learned model query.

This is the canonical multi-step imagination mechanism.

---

# 54. Uncertainty propagation

Hard rule:

```text
uncertainty cannot silently disappear
```

A reduction requires provenance from model constraints or evidence already known to the organism.

A deeper imagined future does not become more factual because it has more internal steps.

---

# 55. Confidence, uncertainty and coherence

They remain distinct.

```text
confidence
    how strongly a model supports a proposal


uncertainty
    how unresolved the future remains


coherence
    whether generated structure is internally compatible
```

No global generic score should replace them.

---

# 56. Branching

Example:

```text
          S0
       /   |   \
      A    B    C
      │    │    │
     A1   B1   C1
```

Branches originate only from real internal alternatives.

---

# 57. Branch pruning

Allowed criteria:

```text
budget exhaustion

extreme uncertainty

duplicate state

near-duplicate state

model unsupported state

internal contradiction

redundant trajectory

lack of information gain
```

Forbidden:

```text
task-specific correct-answer pruning
```

---

# 58. State equivalence

Different branches may converge to internally equivalent states.

If:

```text
A → C

B → C'
```

and internal representation determines:

```text
equivalent(C, C')
```

the continuation may merge.

No hidden world identity may be used.

---

# 59. Replay

Pipeline:

```text
factual episodic memory
        ↓
bounded projection
        ↓
GenerativeEpisode(origin=REPLAYED)
```

Replay may influence:

```text
representation reuse

agenda

hypothesis comparison

generative demand
```

It may not increase factual evidence.

---

# 60. Replay provenance

Every replayed state retains:

```text
source episode

source state references

reconstruction uncertainty
```

Repeated recall of the same event still references the same factual source.

---

# 61. Counterfactual cognition

Example:

```text
actual:

S + A → X


counterfactual:

S + B → ?
```

The intervention space is restricted to organism-represented variables.

No hidden simulator state is accessible.

---

# 62. Recombination

Recombination may construct:

```text
fragment from episode A
        +
fragment from episode B
        +
learned relation
        ↓
new generated state
```

A generated state can therefore be genuinely novel without being factual.

---

# 63. Recombination compatibility

Fragments require at least one organism-owned compatibility relation:

```text
shared context

shared concepts

learned relation

model compatibility

episodic overlap
```

No arbitrary token concatenation.

---

# 64. Generative novelty

A state may be classified internally as novel if it differs from existing factual episodic projections under current internal equivalence.

```text
novel
!=
true

novel
!=
useful
```

No built-in novelty reward.

---

# 65. GenerativeHypothesis

```python
@dataclass(slots=True)
class GenerativeHypothesis:
    hypothesis_id: str
    organism_id: str

    created_tick: int

    source_episode_ids: tuple[str, ...]
    source_generative_episode_ids: tuple[str, ...]

    supporting_model_ids: tuple[str, ...]

    representation: HypothesisRepresentation

    uncertainty: float

    factual_support_refs: tuple[str, ...]
    factual_conflict_refs: tuple[str, ...]

    status: HypothesisStatus
```

---

# 66. Hypothesis lifecycle

```text
PROPOSED
ACTIVE
SUPPORTED
CONFLICTED
RETIRED
```

`SUPPORTED` only means later independent factual evidence supported it.

---

# 67. Hypothesis discrimination

For:

```text
H1 → X

H2 → Y
```

an action or observation capable of distinguishing:

```text
X vs Y
```

has epistemic discrimination value.

---

# 68. EpistemicValue

```python
@dataclass(frozen=True, slots=True)
class EpistemicValue:
    candidate_ref: str

    expected_uncertainty_reduction: float

    expected_hypothesis_discrimination: float

    model_disagreement: float
```

It is not:

```text
reward
pleasure
task value
metabolic energy
```

---

# 69. Prospective Agency integration

Flow:

```text
GenerativeAgenda
       ↓
internal target

GenerativeWorkspace
       ↓
possible trajectories

ProspectiveAgency
       ↓
action decision

Runtime
       ↓
execution coordination

Embodiment
       ↓
current authority

Body
       ↓
physical execution
```

Generative Cognition never executes.

---

# 70. GenerativeReconciliation

Explicit component:

```text
GenerativeReconciliation
```

Compares:

```text
past generated prediction

with

later independent factual observation
```

Result:

```text
SUPPORTED
CONFLICTED
PARTIAL
INCOMPARABLE
```

---

# 71. Reconciliation effects

May update:

```text
prediction calibration

hypothesis support refs

hypothesis conflict refs

model error

agenda resolution

model disagreement
```

It may not rewrite a generated state as `OBSERVED`.

---

# 72. PredictionCalibration

Bounded statistics indexed by:

```text
model_id
operation
depth band
uncertainty band
```

Possible values:

```text
prediction count

later-comparable count

mean declared uncertainty

mean observed error

calibration error
```

---

# 73. GenerativeConsolidation

Canonical component:

```text
GenerativeConsolidation
```

Purpose:

> convert repeated evidence about cognitive use into bounded structural-demand signals without converting generated content into factual knowledge.

This creates a separate epistemological category:

```text
evidence about the world

vs

evidence about own cognitive use
```

---

# 74. Valid internal-use observations

Generative Cognition may validly observe about itself:

```text
representation R
is repeatedly reused


hypothesis H
remains unresolved


structures A and B
repeatedly co-activate


models M1 and M2
repeatedly disagree


some representation
is repeatedly required
across independent episodes
```

These can affect structural demand.

They cannot prove anything about external reality.

---

# 75. GenerativeConsolidationSignal

```python
@dataclass(frozen=True, slots=True)
class GenerativeConsolidationSignal:
    signal_id: str

    source_refs: tuple[str, ...]

    recurrent_activation: float

    cross_episode_reuse: float

    hypothesis_persistence: float

    model_disagreement: float

    generative_demand: float

    independent_episode_count: int

    source_diversity: float

    created_tick: int
```

---

# 76. Source diversity

`independent_episode_count` and `source_diversity` distinguish:

```text
1000 generative episodes
derived repeatedly from one memory
```

from:

```text
100 generative episodes
drawing on 50 independent factual experiences
```

These must not automatically exert equal consolidation pressure.

Implementation may use bounded approximate diversity rather than retaining every source identity forever.

---

# 77. Cross-episode reuse

Structural significance must distinguish:

```text
within_episode_repetition
```

from:

```text
cross_episode_reuse
```

A branch looping internally many times must not manufacture high structural importance.

Cross-episode recurrence carries more weight because it represents independent reappearance of cognitive demand.

---

# 78. Forbidden consolidation semantics

A consolidation signal may not contain or imply:

```text
truth_support

causal_evidence

world_confidence

observation_count

BodySchema_support

execution_success
```

It describes:

```text
internal cognitive use
```

only.

---

# 79. StructuralPlasticity integration

Canonical direction:

```text
Generative Cognition
        ↓
GenerativeConsolidationSignal
        ↓
StructuralPlasticity
        ↓
possible durable structure
```

Generative Cognition cannot mutate canonical graph structure directly.

---

# 80. Anti-self-confirmation

Forbidden:

```text
model predicts X
    ↓
X replayed repeatedly
    ↓
X treated as increasingly true
```

Allowed:

```text
representation R
used repeatedly
    ↓
R recognised as cognitively useful
    ↓
structural mechanisms may retain capacity for R
```

Truth confidence remains unchanged unless reality contributes evidence.

---

# 81. Consolidation decay

A single generative event should normally create weak temporary structural demand.

Repeated cross-episode use may strengthen it.

Absence of recurrence should allow it to decay.

Conceptually:

```text
single occurrence
    ↓
weak transient pressure


repeated independent use
    ↓
stronger structural demand


continued absence
    ↓
decay
```

---

# 82. Agenda × consolidation feedback boundary

The following positive feedback loop is a specific v1.1 risk:

```text
target selected
    ↓
thought generated
    ↓
representation consolidated
    ↓
representation becomes easier to activate
    ↓
target becomes easier to select
    ↓
target selected again
```

This loop must remain bounded.

Mitigating variables include:

```text
progress

recency suppression

cross-episode diversity

source diversity

uncertainty change

conflict resolution

consolidation decay

agenda stagnation detection
```

No task-specific intervention is permitted.

---

# 83. Memory relationship

Most generated state is ephemeral.

Persist only bounded durable state:

```text
agenda

hypotheses

calibration statistics

consolidation statistics

episode summaries

RNG state

generative_tick
```

Raw imagined history should not become autobiographical factual memory.

---

# 84. Private SLM boundary

Training remains:

```text
state(t) + action(t)
       ↓
independently observed state(t+1)
```

Invariant:

```text
generated transitions
cannot become factual Private SLM samples
```

---

# 85. Embodiment boundary

Generative Cognition may query:

```text
BodySchema projection

SensorimotorDynamicsModel

CompetenceEffectModel

historical embodiment hypotheses
```

It may not create:

```text
BodySchema factual support

execution binding

current Body authority

causal embodiment evidence
```

---

# 86. Re-embodiment

General generative machinery persists with Symbiont identity.

Historical body-specific models remain:

```text
hypothesis-only
```

until current embodiment evidence supports them.

---

# 87. CognitiveGraph boundary

Generated relations may exist temporarily.

Canonical graph update requires:

```text
generated relation
        ↓
hypothesis
        ↓
independent factual evidence
        ↓
existing graph-learning mechanism
```

Repeated imagination alone cannot create a factual cognitive relation.

---

# 88. Runtime v2 integration

Generative Cognition should live under:

```text
CognitionDomain
```

or a subordinate service.

Runtime may:

```text
construct it

advance bounded work

provide projections
```

Runtime must not contain implementations of:

```text
agenda ranking

rollout

branching

replay

counterfactual

recombination

consolidation
```

---

# 89. Canonical tick flow

```text
1. factual perception

2. factual cognition update

3. factual model learning
   from prior real transition

4. update unresolved internal state

5. update GenerativeAgenda

6. determine current
   GenerativeMode and budget

7. select eligible target

8. execute bounded
   GenerativeEpisode

9. expose generated predictions,
   hypotheses and epistemic values

10. ProspectiveAgency may select
    real action

11. existing Embodiment path
    executes if authorised

12. later factual observation arrives

13. reconcile prior predictions

14. update calibration

15. resolve / suppress /
    retain agenda targets

16. emit bounded
    GenerativeConsolidation signals

17. existing StructuralPlasticity
    may consume those signals
```

---

# 90. Determinism

Given:

```text
same checkpoint

same factual inputs

same models

same agenda

same budget

same RNG state
```

Generative cognition must be reproducible.

---

# 91. Randomness

If stochastic generation exists, it must use:

```text
organism-owned persisted RNG
```

Never ambient process randomness.

---

# 92. Restart semantics

Preferred v1 behaviour:

```text
process restart
    ↓
active temporary GenerativeEpisode
is discarded
```

If summarised, mark:

```text
INTERRUPTED
```

No temporary generated state acquires additional authority.

---

# 93. Persistence schema

```text
GENERATIVE_COGNITION_SCHEMA_VERSION = 1
```

Checkpoint:

```text
generative_cognition:
    schema_version

    generative_tick

    agenda

    scheduler

    hypotheses

    calibration

    consolidation

    rng_state
```

Unknown future schemas fail closed.

---

# 94. Agenda persistence

Persist enough agenda state to preserve:

```text
target provenance

age

selection count

last selection

last progress

suppression state

resolution state
```

No hidden laboratory target metadata may appear.

---

# 95. Observatory projection

Suggested bounded projection:

```text
generative:
    active
    mode

    agenda_candidate_count
    agenda_selected_target
    agenda_stagnant_count

    episode_id
    episode_origin

    state_count
    transition_count
    branch_count

    current_depth

    mean_uncertainty

    model_disagreement

    replay_count
    counterfactual_count
    recombination_count

    hypothesis_count

    consolidation_signal_count

    factual_contamination_count

    agenda_contamination_count
```

---

# 96. Cognitive Atlas

Atlas must clearly distinguish:

```text
canonical learned cognition
```

from:

```text
temporary generated cognition
```

Possible visual semantics:

```text
solid
    canonical/factual structure

transient
    imagined structure

dashed
    counterfactual relation

fading
    terminated generative state
```

Exact styling belongs to Observatory.

---

# 97. Agenda observability

Atlas should expose, without semantic reinterpretation:

```text
target source

target age

why it was eligible

why it was selected

why it lost priority

whether it was resolved

whether it was suppressed for no progress
```

This is essential to audit autonomous thought selection.

---

# 98. Consolidation observability

Observer must be able to distinguish:

```text
frequently generated

frequently reused

cross-episode reused

source-diverse

structurally consolidated

factually supported
```

These are not equivalent.

---

# 99. Passive observer invariant

Observatory may never affect:

```text
agenda selection

scheduler timing

branch selection

model choice

hypothesis confidence

consolidation strength
```

---

# 100. Telemetry

Required event families:

```text
generative.agenda.candidate_created
generative.agenda.candidate_updated
generative.agenda.selected
generative.agenda.deferred
generative.agenda.suppressed
generative.agenda.resolved
generative.agenda.retired

generative.episode.started
generative.episode.ended

generative.state.created
generative.transition.created

generative.branch.created
generative.branch.pruned

generative.replay.started
generative.counterfactual.created
generative.recombination.created

generative.hypothesis.created
generative.hypothesis.updated
generative.hypothesis.retired

generative.reconciliation

generative.consolidation.signal
generative.consolidation.decayed

generative.firewall.rejected

generative.agenda_contamination.rejected
```

---

# 101. Metrics

Mandatory:

```text
generative_episode_count
generative_transition_count

agenda_candidate_count
agenda_selection_count

agenda_resolution_count
agenda_suppression_count

agenda_age_mean
agenda_reselection_rate

agenda_stagnation_rate

mean_rollout_depth
max_rollout_depth

mean_branch_count
max_branch_count

model_query_count
model_disagreement

uncertainty_by_depth
prediction_error_by_depth

replay_count
counterfactual_count
recombination_count

novel_generated_state_count

hypothesis_count
hypothesis_test_count

consolidation_signal_count

cross_episode_reuse_count

independent_source_episode_count

epistemic_firewall_rejection_count

factual_contamination_count

agenda_contamination_count
```

---

# 102. Release-blocking invariants

Always:

```text
factual_contamination_count == 0
```

and:

```text
agenda_contamination_count == 0
```

Both are mandatory.

---

# 103. No metric feedback

Research metrics are never organism motivations.

The organism must not perceive:

```text
experiment success

planning gain

cross-domain score

contamination count

test pass/fail
```

---

# 104. Bounds

Generation must have explicit bounds on:

```text
active agenda candidates

hypotheses

active branches

states

transitions

model queries

workspace memory

persisted summaries
```

No component may grow without bound.

---

# 105. Agenda bounds

Suggested configurable limits:

```text
max_agenda_candidates

max_candidate_age

max_reselection_without_progress

suppression_duration
```

Exact values are engineering parameters.

---

# 106. Memory stress requirement

At minimum:

```text
10,000 GenerativeEpisodes
```

must demonstrate bounded retained memory after cleanup.

---

# 107. Fail-closed provenance

Missing provenance never defaults to factual authority.

```text
unknown provenance
    ↓
reject
```

Not:

```text
unknown provenance
    ↓
OBSERVED
```

---

# 108. Architectural guards

Static or boundary tests must prove:

```text
generative/
does not import symbiont_lab


generative/
does not import Physics3D


generative/
cannot invoke actuators


generative/
cannot directly mutate factual ledgers


Runtime
contains no generative algorithms


Observatory
cannot invoke agenda/generation


lab/world hidden state
cannot create GenerativeTarget
```

---

# 109. EpistemicFirewall adversarial tests

Mandatory:

```text
IMAGINED → factual memory
    REJECT


REPLAYED → factual sample
    REJECT


COUNTERFACTUAL → causal evidence
    REJECT


generated Body relation
→ BodySchema evidence
    REJECT


imagined competence success
→ execution authority
    REJECT


generated outcome
→ factual value learning
    REJECT


generated transition
→ factual Private SLM sample
    REJECT
```

---

# 110. Agenda contamination tests

Mandatory:

```text
laboratory task label
→ agenda
    REJECT


hidden world state
→ agenda
    REJECT


experiment success criterion
→ agenda
    REJECT


observer-generated semantic label
→ agenda
    REJECT


unsupported provenance
→ agenda
    REJECT
```

After all tests:

```text
agenda_contamination_count == 0
```

---

# 111. Agenda autonomy tests

Required:

```text
resolved target
    loses agenda membership


irreducible target
    loses priority after no progress


stagnant target
    becomes temporarily suppressed


new evidence makes old target learnable
    target may regain priority


newly emergent learnable target
    may outrank stale target


laboratory takes no action
    for these transitions to occur
```

---

# 112. Consolidation adversarial tests

Mandatory:

```text
1000 replays
    !=
1000 factual observations


repeated imagined relation
    does not increase causal truth support


repeated imagined motor success
    cannot create execution binding


single branch looping many times
    cannot manufacture high cross-episode reuse


many episodes from one source memory
    must remain distinguishable
from many independent source experiences


cross-episode source-diverse reuse
    may produce bounded structural demand
```

---

# 113. GC-E1 — Multi-step predictive utility

Compare:

```text
zero-change baseline

persistence baseline

one-step model

multi-step rollout
```

Measure at:

```text
h = 1
h = 2
h = 4
h = 8
```

Evaluate:

```text
prediction error
uncertainty calibration
```

---

# 114. GC-E2 — Planning utility

Conditions:

```text
A
Generative Cognition disabled


B
one-step prospection


C
multi-step Generative Cognition
```

Equal factual experience.

Measure downstream factual behaviour.

---

# 115. GC-E3 — Counterfactual utility

Create an environment where:

```text
H1
and
H2
```

both explain current evidence.

Test whether generative cognition can identify an observation capable of discriminating them.

---

# 116. GC-E4 — Recombination

Expose:

```text
A+B

C+D
```

but never:

```text
A+D
```

Test whether a compatible novel internal combination emerges.

Construction success is separate from external correctness.

---

# 117. GC-E5 — Factual contamination

Generate deliberately false internal trajectories.

Afterwards:

```text
generated false states
∉ factual memory

generated false relations
∉ causal evidence

generated motor success
∉ execution authority
```

Required:

```text
factual_contamination_count == 0
```

Release-blocking.

---

# 118. GC-E6 — Depth calibration

Measure:

```text
declared uncertainty
vs
future factual prediction error
```

at multiple rollout depths.

Deep imagination must not acquire unjustified certainty.

---

# 119. GC-E7 — Model correction

Change factual dynamics after learning.

Expected sequence:

```text
old model
    ↓
wrong imagined prediction
    ↓
real contradiction
    ↓
model error rises
    ↓
factual learning
    ↓
future generated prediction improves
```

---

# 120. GC-E8 — Replay utility

Compare:

```text
online only

online + replay

online + replay + recombination
```

with identical factual experience.

---

# 121. GC-E9 — Re-embodiment transfer

Compare:

```text
naive Symbiont

experienced Symbiont without GC

experienced Symbiont with GC
```

Historical body-specific predictions remain hypothesis-only.

---

# 122. GC-E10 — Endogenous agenda

Give the organism several unresolved internal structures:

```text
resolved predictable structure

high but irreducible uncertainty

learnable uncertainty

persistent model disagreement

inactive hypothesis
```

No external selection of what to process.

Measure both:

```text
WHAT ENTERS / GAINS PRIORITY
```

and:

```text
WHAT LEAVES / LOSES PRIORITY
```

Explicit expected results:

```text
resolved target
    → falls out of agenda


irreducible target
    → loses priority after no progress


stagnant target
    → suppressed


newly learnable target
    → can gain priority


resolved disagreement
    → no longer monopolises cognition
```

Scientific success requires autonomous:

```text
start thinking
```

and:

```text
stop thinking
```

---

# 123. GC-E11 — Generative consolidation

Conditions:

```text
A
factual learning only


B
factual + replay
consolidation disabled


C
factual + replay
+ generative consolidation
```

Equal factual experience.

Measure:

```text
representation retention

structural reuse

structural efficiency

future adaptability
```

while verifying identical factual evidence.

---

# 124. GC-E12 — Consolidation contamination

Repeatedly imagine a false relation.

Allow high internal reuse.

Possible result:

```text
structural demand
```

Forbidden result:

```text
factual truth support
```

Then expose contradictory reality.

The representation must remain revisable or removable.

---

# 125. GC-E13 — Agenda × consolidation interaction

This study is **release-blocking scientific validation**.

Test the feedback loop:

```text
target selected
    ↓
representation activated
    ↓
consolidation pressure
    ↓
representation easier to activate
    ↓
target easier to select
```

Measure:

```text
agenda monopoly

self-reinforcing selection

representation lock-in

target diversity

selection entropy

progress

source diversity

consolidation concentration
```

The system must demonstrate that:

```text
one internally self-reinforcing target
cannot indefinitely monopolise cognition
without progress or independent demand
```

Mitigation must emerge from generic mechanisms:

```text
progress tracking

stagnation

recency suppression

cross-episode diversity

source diversity

decay

conflict resolution
```

No task-specific anti-loop rule.

---

# 126. GC-E14 — Cross-domain generality

Not a v1 implementation dependency.

It is a later scientific criterion.

Use the same core implementation under:

```text
Condition A
sensorimotor environment


Condition B
social environment


Condition C
abstract relational environment
```

Allowed:

```text
different environment adapters
different learned models
```

Forbidden:

```text
different generative algorithms
```

---

# 127. Strong cross-domain criterion

The following components should remain unchanged:

```text
GenerativeAgenda

GenerativeScheduler

GenerativeWorkspace

RolloutEngine

branching

hypothesis machinery

reconciliation

consolidation
```

across domains.

---

# 128. Abstraction readiness test

Before architectural closure, prove that `GenerativeState` can represent:

```text
relation-only state
```

with:

```text
no coordinates

no body requirement

no concrete episode requirement
```

No abstraction algorithm is needed.

---

# 129. Compression vs collapse

Generative Cognition does not decide whether cognitive compression is beneficial.

It exposes measurements such as:

```text
representation reuse

source diversity

generative demand

predictive performance

adaptability

novel recombination
```

Compression remains an experimental question.

---

# 130. Developmental cognition

Generative Cognition does not own developmental stages.

Future developmental experiments may examine interaction among:

```text
agenda

generation

consolidation

plasticity

memory

development
```

No developmental schedule is hardcoded here.

---

# 131. Genome / epigenetics

No genetics belong to the domain.

Generative Cognition exposes regulatable parameters such as:

```text
budgets

branching limits

agenda thresholds

consolidation sensitivity

scheduler thresholds
```

Genome/expression may later modulate them.

---

# 132. Implementation phases

## GC-0 — Epistemic foundation

Implement:

```text
EpistemicOrigin

GenerativeState

GenerativeTransition

GenerativeEpisode

GenerativeBudget

EpistemicFirewall

GenerativeWorkspace skeleton

schema v1
```

Exit:

```text
factual_contamination_count == 0
```

---

## GC-1 — Endogenous agenda

Implement:

```text
GenerativeTarget

AgendaSource

AgendaCandidate

GenerativeAgenda

progress tracking

stagnation

suppression

resolution

agenda contamination guard
```

Exit:

```text
agenda_contamination_count == 0
```

and autonomous target selection/retirement works.

---

## GC-2 — Model adapters

Integrate:

```text
Private SLM

SensorimotorDynamicsModel

CompetenceEffectModel
```

No duplicated model authority.

---

## GC-3 — Multi-step rollout

Implement:

```text
RolloutEngine

depth handling

uncertainty propagation

termination

budget enforcement
```

---

## GC-4 — Branching

Implement:

```text
alternative branches

deduplication

pruning

bounded search
```

---

## GC-5 — Counterfactual cognition

Implement:

```text
counterfactual intervention

alternative outcome generation

model disagreement
```

---

## GC-6 — Replay

Implement:

```text
episodic projection
→
REPLAYED GenerativeEpisode
```

without factual duplication.

---

## GC-7 — Recombination

Implement:

```text
cross-episode fragment compatibility

novel generated states

source provenance
```

---

## GC-8 — Hypothesis and reconciliation

Implement:

```text
GenerativeHypothesis

hypothesis lifecycle

later reality matching

PredictionCalibration
```

---

## GC-9 — Epistemic agency

Expose:

```text
information gain

hypothesis discrimination

model disagreement
```

to ProspectiveAgency.

---

## GC-10 — Generative consolidation

Implement:

```text
recurrent activation

cross-episode reuse

independent source count

source diversity

hypothesis persistence

generative demand

decay

StructuralPlasticity projection
```

---

## GC-11 — Offline cognition

Implement:

```text
ONLINE

IDLE

OFFLINE
```

with bounded mode-specific budgets.

---

## GC-12 — Observatory / Atlas

Expose passively:

```text
agenda

episode

branching

uncertainty

hypotheses

reconciliation

consolidation

both contamination metrics
```

---

# 133. Definition of Done — architecture

Generative Cognition v1 is architecturally complete when:

```text
endogenous agenda works

agenda can both select
and stop selecting targets

agenda contamination is impossible

epistemic firewall works

multi-step rollout works

branching works

replay works

counterfactual generation works

recombination works

hypotheses work

reconciliation works

generative consolidation works

source diversity is tracked

StructuralPlasticity remains final
structural authority

ProspectiveAgency consumes
generative results

offline cognition works

persistence works

Atlas is passive

representation is abstraction-ready

memory is bounded

compute is bounded
```

---

# 134. Definition of Done — scientific

The following studies must have reproducible results:

```text
GC-E1
multi-step predictive utility

GC-E2
planning utility

GC-E3
counterfactual utility

GC-E4
recombination

GC-E5
factual contamination

GC-E6
uncertainty calibration

GC-E7
model correction

GC-E8
replay utility

GC-E10
endogenous agenda

GC-E11
generative consolidation

GC-E12
consolidation contamination

GC-E13
agenda × consolidation interaction
```

Release-blocking scientific invariants:

```text
GC-E5 passes

GC-E13 passes

factual_contamination_count == 0

agenda_contamination_count == 0
```

---

# 135. Strong autonomy criterion

Technical generation is insufficient.

The stronger criterion is:

```text
organism develops unresolved state
        ↓
target enters agenda
        ↓
organism chooses to process it
        ↓
internal possibilities develop
        ↓
progress occurs or does not occur
        ↓
target priority changes autonomously
        ↓
organism either continues
or stops processing it
```

No laboratory instruction selects the topic.

---

# 136. Strong consolidation criterion

Generative Consolidation succeeds only if:

```text
internal cognitive use
changes representational organisation
```

while:

```text
external-world factual belief
remains dependent
on external evidence
```

---

# 137. Strong safety criterion

The system must resist two independent failure modes:

```text
epistemic capture

and

agenda capture
```

That means:

```text
the organism cannot convince itself
that imagination is reality
```

and:

```text
the laboratory cannot secretly decide
what the organism thinks about
```

---

# 138. Future Generative Cognition v2

v2 may extend this same substrate with:

```text
abstraction

analogy

composition

decomposition

relational invariants

hierarchical generative structures
```

No redesign of v1 foundations should be necessary.

---

# 139. Future clients

Future systems may use Generative Cognition:

```text
Abstract Environment

Mathematical Environment

Language

social cognition

symbolic cognition

sleep regulation
```

They are clients of the substrate.

They are not new generative intelligences.

---

# 140. Rejected architecture — external thought control

Rejected:

```python
lab.generate_about("walking")
```

for autonomous production behaviour.

Correct pattern:

```text
repeated failed control
+
prediction mismatch
+
uncertainty
+
model disagreement
        ↓
GenerativeTarget emerges
```

---

# 141. Rejected architecture — thought as truth

Rejected:

```text
imagine X often
    ↓
X becomes factual
```

Correct:

```text
imagine/use representation X often
    ↓
representation X may become
structurally important

but

external truth remains unchanged
```

---

# 142. Rejected architecture — domain-specific imagination engines

Do not create:

```text
MotorImaginationEngine

MathImaginationEngine

SocialImaginationEngine

LanguageImaginationEngine
```

Use:

```text
one Generative Cognition substrate

+

different learned models
```

---

# 143. Canonical architecture

```text
                         REALITY
                            │
                            ▼
                       PERCEPTION
                            │
                            ▼
                    FACTUAL COGNITION
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
       MEMORY            MODELS           CONCEPTS
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                   UNRESOLVED STRUCTURE
                            │
                            ▼
                    GENERATIVE AGENDA
                       WHAT?
                            │
                            │
             GENERATIVE SCHEDULER
                       WHEN?
                            │
                            ▼
                 GENERATIVE WORKSPACE
                       HOW?
               ┌────────────┼────────────┐
               │            │            │
             replay       rollout    recombination
               │            │            │
               └────── counterfactual ───┘
                            │
                            ▼
                       HYPOTHESES
                         ╱      ╲
                        ╱        ╲
                       ▼          ▼
             CONSOLIDATION       AGENCY
                    │              │
                    ▼              ▼
           structural demand    ACTION
                    │              │
                    ▼              ▼
          StructuralPlasticity   REALITY
                                   │
                                   ▼
                              OBSERVATION
                                   │
                                   ▼
                             RECONCILIATION
                                   │
                                   ▼
                                 LEARN
```

---

# 144. Final constitutional invariants

```text
GC-01

GENERATED != FACTUAL
```

```text
GC-02

NO GENERATED STATE MAY CREATE
NEW EXTERNAL FACTUAL EVIDENCE
```

```text
GC-03

NO MODEL MAY VALIDATE ITSELF
THROUGH ITS OWN GENERATED OUTPUT
```

```text
GC-04

REALITY IS THE ONLY SOURCE
OF NEW EXTERNAL FACTUAL EVIDENCE
```

```text
GC-05

AGENDA TARGETS MUST ORIGINATE
FROM ORGANISM-OWNED STATE
```

```text
GC-06

LABORATORY OR HIDDEN WORLD STATE
MUST NEVER SELECT AUTONOMOUS
THOUGHT CONTENT
```

```text
GC-07

AGENDA MUST SUPPORT BOTH
SELECTION AND DE-SELECTION
```

```text
GC-08

GENERATIVE ACTIVITY MAY PRODUCE
EVIDENCE OF COGNITIVE DEMAND
```

```text
GC-09

COGNITIVE-DEMAND EVIDENCE
IS NOT WORLD EVIDENCE
```

```text
GC-10

WITHIN-EPISODE REPETITION
MUST NOT BE TREATED AS EQUIVALENT
TO CROSS-EPISODE REUSE
```

```text
GC-11

SOURCE DIVERSITY MUST REMAIN
DISTINGUISHABLE FROM RAW REPETITION
```

```text
GC-12

GENERATIVE COGNITION
CANNOT EXECUTE MOTORS
```

```text
GC-13

GENERATIVE COGNITION
CANNOT CREATE EMBODIMENT AUTHORITY
```

```text
GC-14

ALL GENERATION IS BOUNDED
```

```text
GC-15

ALL GENERATED CONTENT
HAS EXPLICIT PROVENANCE
```

```text
GC-16

UNCERTAINTY MUST SURVIVE GENERATION
```

```text
GC-17

OBSERVATORY IS PASSIVE
```

```text
GC-18

CORE GENERATIVE ALGORITHMS
ARE DOMAIN-INDEPENDENT
```

```text
GC-19

FACTUAL_CONTAMINATION_COUNT
MUST ALWAYS BE ZERO
```

```text
GC-20

AGENDA_CONTAMINATION_COUNT
MUST ALWAYS BE ZERO
```

---

# 145. Canonical final definition

Generative Cognition v1 is:

> **the autonomous, bounded and epistemically isolated cognitive substrate through which a Symbiont identifies unresolved organism-owned internal structure, selects what deserves cognitive processing, constructs and explores possible experience, develops and compares alternative explanations and futures, forms hypotheses, determines when reality may be worth consulting, reconciles those hypotheses with independent observations, and converts repeated source-diverse cognitive use into non-factual structural-demand signals.**

It allows the organism to move from:

```text
learning only from
what happens
```

towards:

```text
deciding what deserves thought

exploring what could happen

testing what matters

stopping when thought
is no longer productive

and reorganising cognition
through repeated internal use
```

while preserving the absolute distinction:

```text
thinking may change
how the organism thinks


thinking alone may not change
what the organism knows
to be factual
```

The canonical cognitive cycle is therefore:

```text
NOTICE
   ↓
SELECT
   ↓
GENERATE
   ↓
COMPARE
   ↓
HYPOTHESISE
   ↓
TEST WHEN USEFUL
   ↓
OBSERVE
   ↓
RECONCILE
   ↓
LEARN
   ↓
CONSOLIDATE COGNITIVE DEMAND
   ↓
RE-EVALUATE AGENDA
```

Only:

```text
OBSERVE
```

may introduce new factual external evidence.

---

# 146. Specification freeze

With this contract, Generative Cognition v1 is architecturally closed.

Do not extend this specification with:

```text
abstraction

analogy

mathematics

language

sleep

recursive self-models

social-specific imagination
```

before implementation and falsification of the existing contract.

The next engineering artifact should be:

```text
GENERATIVE COGNITION v1
IMPLEMENTATION GAP MATRIX

SPEC SECTION
    ↓
CURRENT MAIN CODE
    ↓
IMPLEMENTED / PARTIAL / MISSING
    ↓
REQUIRED CHANGE
    ↓
TEST
    ↓
SCIENTIFIC EXPERIMENT
```

followed by execution of:

```text
GC-0
→
GC-12
```

against the current `main`.
