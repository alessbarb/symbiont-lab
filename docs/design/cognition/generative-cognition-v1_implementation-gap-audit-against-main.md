# Generative Cognition v1 — Implementation GAP Audit against `main`

**Repository:** `alessbarb/symbiont-lab`
**Audited branch:** `main`
**Audited commit:** `d8bb94f0`
**Spec:** Generative Cognition v1 — frozen candidate
**Scope:** GC-0 → GC-12
**Purpose:** map canonical specification to existing implementation and define the exact remaining work, tests and scientific closure conditions.

---

# 1. Executive conclusion

Generative Cognition v1 is:

```text
architecturally specified
but
not yet implemented as a domain
```

The repository already contains strong prerequisites:

```text
epistemic provenance primitives
anti-self-confirmation rules

factual episodic memory
episodic projection
episodic recurrence/provenance

one-step counterfactual prediction

ProspectiveAgency
OutcomeValueLedger

private predictive model
factual prediction reconciliation

MemoryConsolidator

StructuralContention
StructuralPlanner
RepresentationTracker

Runtime v2 domains

Cognitive Atlas v2
passive observer projection
```

What does **not** yet exist after the foundation, agenda, and registry increments:

```text
multi-step rollout

generic branching

generic replay-as-generative-state

generic counterfactual state manipulation

recombination

GenerativeHypothesis lifecycle

generic reconciliation

EpistemicValue

GenerativeConsolidationSignal

ONLINE / IDLE / OFFLINE generative modes

generative Atlas projection
```

Therefore:

```text
Generative Cognition v1
is not a refactor of one existing component.

It is a new cognitive substrate
built by composing several mature existing components.
```

---

# 2. Global implementation status

| Phase | Capability | Current status |
|---|---|---|
| GC-0 | Epistemic foundation | **IMPLEMENTED — bounded foundation** |
| GC-1 | Endogenous agenda | **IMPLEMENTED — bounded agenda and scheduler substrate** |
| GC-2 | Generative model adapters | **IMPLEMENTED — thin adapters; runtime integration pending** |
| GC-3 | Multi-step rollout | **IMPLEMENTED — bounded rollout substrate; integration and scientific utility pending** |
| GC-4 | Branching | **PARTIAL — bounded sibling branch substrate; pruning/equivalence/merge pending** |
| GC-5 | Counterfactual cognition | **PARTIAL — bounded generic rollout substrate; concrete adapters and utility pending** |
| GC-6 | Replay | **IMPLEMENTED — provenance-preserving materialization; concrete memory wiring pending** |
| GC-7 | Recombination | **PARTIAL — compatibility-gated fragment composition; novelty/equivalence evidence pending** |
| GC-8 | Hypothesis + reconciliation | **PARTIAL — lifecycle/reconciliation/calibration substrate; runtime evidence pending** |
| GC-9 | Epistemic agency | **PARTIAL — pragmatic agency exists** |
| GC-10 | Generative consolidation | **PARTIAL — structural substrate exists** |
| GC-11 | Offline cognition | **MISSING** |
| GC-12 | Observatory / Atlas | **PARTIAL — observer substrate excellent** |

The critical path is therefore approximately:

```text
GC-0
 ↓
GC-1 + GC-2
 ↓
GC-3
 ↓
GC-4 / GC-5 / GC-6
 ↓
GC-7
 ↓
GC-8
 ↓
GC-9
 ↓
GC-10
 ↓
GC-11
 ↓
GC-12
```

GC-1 and GC-2 can be developed largely independently after GC-0.

---

# 3. GC-0 — Epistemic foundation

## Spec coverage

Relevant specification areas:

```text
§9–20   epistemic ontology / authority
§21–28  core representation
§90–94  determinism / persistence
§102    release-blocking invariants
§107–110 adversarial boundaries
```

## Current code

Strong reusable components already exist.

### `src/symbiont/modeling/experience.py`

Existing:

```python
class EpistemicStatus:
    OBSERVED
    ASSOCIATED
    HYPOTHESIZED
    PREDICTED
    SUPPORTED
    CONTRADICTED
    RETIRED
```

Existing source classification:

```python
class SourceKind:
    DIRECT
    INTERNAL
    ACTION_OUTCOME
    COGNITIVE
    MODEL
```

Critically, `ExperienceRecord` already rejects:

```text
SourceKind.MODEL
+
EpistemicStatus.OBSERVED
```

This is an existing anti-self-confirmation invariant.

### `src/symbiont/agency/types.py`

`CounterfactualPrediction` explicitly states:

```text
model-generated
counterfactual
never recorded as observed experience
```

### `src/symbiont/modeling/private_runtime.py`

Observed transitions are constructed only after:

```text
state(t)
+
action(t)
+
independently observed state(t+1)
```

and are recorded as:

```text
EpistemicStatus.OBSERVED
```

Model predictions are recorded separately as:

```text
PREDICTED
MODEL
```

and later become:

```text
SUPPORTED
or
CONTRADICTED
```

only through comparison with factual experience.

This is already extremely close to the epistemic philosophy required by Generative Cognition.

---

## Remaining implementation

The canonical package now exists:

```text
src/symbiont/cognition/generative/
```

At minimum:

```text
types.py
epistemic.py
state.py
transition.py
episode.py
budget.py
workspace.py
persistence.py
```

Implemented in the first foundation increment:

```text
`EpistemicOrigin`, `GenerativeState`, `GeneratedFeature`,
`GenerativeTransition`, `GenerativeEpisode`, `GenerativeOperation`,
`GenerativeTermination`, `GenerativeBudget`, `GenerativeWorkspace` and
`EpistemicFirewall` are implemented in `generative/`.

The remaining GC-0 work is integration with checkpoint/runtime boundaries and
the dedicated experimental-integrity suite.
```

---

## Important design decision

Do **not** replace `EpistemicStatus`.

They represent different dimensions.

Use:

```text
ExperienceRecord.epistemic_status
```

for existing factual/model lifecycle.

Use:

```text
GenerativeState.origin
```

for provenance inside generative cognition.

Conceptually:

```text
EpistemicStatus
    state of a knowledge/experience record

EpistemicOrigin
    provenance of a generative representation
```

They should coexist.

---

## EpistemicFirewall

The firewall should wrap or guard boundary operations rather than introduce parallel factual stores.

It must explicitly reject:

```text
GenerativeState
    → ExperienceLedger OBSERVED

GenerativeTransition
    → factual causal ledger

GenerativeState
    → BodySchema factual evidence

GenerativeTransition
    → execution binding evidence

generated outcome
    → OutcomeValueLedger factual learning

generated transition
    → Private SLM observed corpus
```

---

## Tests

New:

```text
tests/unit/cognition/generative/
    test_state.py
    test_episode.py
    test_epistemic.py
    test_workspace.py
    test_budget.py
    test_persistence.py
```

Experimental-integrity:

```text
tests/experimental_integrity/
    test_generative_factual_boundary.py
    test_generative_runtime_import_boundary.py
```

Mandatory adversarial cases:

```text
IMAGINED → OBSERVED
reject

REPLAYED → factual sample
reject

COUNTERFACTUAL → factual causal support
reject

generated motor success → execution authority
reject
```

---

## Experiment

Foundation experiment:

```text
GC-E5 — Factual contamination
```

Must produce:

```text
factual_contamination_count == 0
```

---

## Status

```text
IMPLEMENTED — foundation only
```

The most important epistemic invariant already exists.

The generic bounded representation and fail-closed persistence now exist.

---

# 4. GC-1 — Endogenous Generative Agenda

## Spec

Relevant:

```text
§29–38
§111
§122 GC-E10
```

## Current code

There is no:

```text
`GenerativeAgenda`, `GenerativeTarget`, `AgendaCandidate` and `AgendaSource`
now exist in `src/symbiont/cognition/generative/agenda.py`.
```

There are, however, useful patterns elsewhere.

### Autonomous private-model training

`ModeledOrganismRuntime` already has:

```python
AutonomousTrainingPlan
```

whose documented contract says:

```text
organism-authored request

host may execute/defer

host does not choose:
trigger
corpus
objective
requested work
```

This is conceptually useful.

It demonstrates an existing architectural philosophy:

```text
organism decides need
host supplies compute
```

GenerativeAgenda should follow the same direction.

---

## Remaining

Implement:

```text
agenda.py
```

with:

```text
AgendaSource
GenerativeTarget
AgendaCandidate
GenerativeAgenda
```

Sources:

```text
PREDICTION_ERROR

MODEL_DISAGREEMENT

ACTIVE_HYPOTHESIS

UNCERTAINTY

EPISODIC_INCOMPLETENESS

PROSPECTIVE_DECISION

RECURRING_CONFLICT
```

---

## Required target lifecycle

Each target needs at least:

```text
created
eligible
selected
deferred
suppressed
resolved
retired
```

and state:

```text
selection_count

last_selected_tick

last_progress_tick

uncertainty

recurrence

persistence

estimated_resolvability
```

---

## Missing anti-rumination machinery

Must introduce generic progress detection.

No progress when repeated processing yields none of:

```text
new branch

uncertainty change

model-disagreement change

new hypothesis

refined hypothesis

new discriminating experiment

successful reconciliation
```

Then:

```text
candidate
→ temporary suppression
```

---

## Agenda contamination

No current generic protection exists because no agenda exists.

Implement separate invariant:

```text
agenda_contamination_count
```

Reject any candidate sourced from:

```text
symbiont_lab evaluator

hidden World state

Physics3D private state

observer classification

task labels

benchmark result
```

---

## Tests

```text
test_agenda.py

test_agenda_selection.py

test_agenda_stagnation.py

test_agenda_resolution.py

test_agenda_persistence.py

test_agenda_contamination.py
```

Key cases:

```text
resolved target disappears

irreducible uncertainty loses priority

stagnant target suppressed

new evidence can reactivate target

lab-created target rejected
```

---

## Experiment

```text
GC-E10 — Endogenous Agenda
```

Must test both:

```text
what starts being selected
```

and:

```text
what stops being selected
```

---

## Status

```text
IMPLEMENTED — agenda substrate
```

This is the first genuinely new autonomous mechanism. Runtime integration and
the GC-E10 campaign remain open.

---

# 5. GC-2 — Generative model adapters

## Spec

Relevant:

```text
§46–50
```

## Current code

Several useful models already exist.

### Private SLM

`PrivateModelOrganismRuntime.predict_competence_outcome()` performs:

```text
context
+
competence
→
predicted outcome
```

without recording an `ExperienceRecord`.

The code explicitly calls this:

```text
an imagination query
```

This is directly reusable.

### Prospective model callback

`ProspectiveAgency.deliberate()` already consumes a callable:

```python
predictor(action_id, context_tokens)
    -> CounterfactualPrediction
```

So model-based cognition already has a clean dependency inversion point.

### Embodiment models

Embodiment v2 already exposes:

```text
SensorimotorDynamicsModel

CompetenceEffectModel
```

for lower and higher-level predictions.

---

## Remaining

The common protocol and deterministic registry now exist:

```text
src/symbiont/cognition/generative/model.py
src/symbiont/cognition/generative/registry.py
```

Initial adapters:

```text
PrivateSLMGenerativeAdapter

SensorimotorDynamicsGenerativeAdapter

CompetenceEffectGenerativeAdapter

EpisodicReplayAdapter
```

---

## Important migration rule

Do not move ownership into the registry.

Correct:

```text
existing model
    ↓
thin adapter
    ↓
GenerativeModel protocol
```

Incorrect:

```text
copy current model state
into Generative Cognition
```

---

## Tests

```text
test_model_protocol.py

test_registry.py

test_private_slm_adapter.py

test_sensorimotor_adapter.py

test_competence_effect_adapter.py
```

Must prove:

```text
adapter query
==
existing direct model query
```

for equivalent one-step conditions.

---

## Experiment

No standalone scientific experiment needed yet.

GC-E1 begins once GC-3 exists.

---

## Status

```text
PARTIAL — protocol and registry implemented
```

The common protocol, deterministic registry, and thin callback adapters for the
private, sensorimotor, competence-effect and episodic model owners exist in
`generative/model.py`, `registry.py` and `adapters.py`. Runtime wiring and
equivalence tests against every concrete owner remain open.

---

# 6. GC-3 — Multi-step Rollout

## Spec

Relevant:

```text
§51–55
§113 GC-E1
```

## Current code

The existing Prospective Agency remains fundamentally one-step, while the new generative substrate now provides a bounded rollout path:

```text
candidate
   ↓
CounterfactualPrediction
   ↓
predicted_outcome
```

`CounterfactualPrediction` contains only:

```text
action_id
predicted_outcome
confidence_class
```

The generative rollout engine now creates bounded generated next states and recursively feeds them back through the registry. It remains a substrate; no production runtime path or scientific utility result is claimed yet.

---

## Implemented substrate

Implemented in:

```text
rollout.py
```

with:

```text
RolloutEngine
RolloutResult
```

The engine must support:

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

and enforce:

```text
max_depth

max_states

max_transitions

max_model_queries

uncertainty propagation
```

---

## Key technical challenge

Existing Private SLM returns an opaque outcome token.

For multi-step rollout, a model adapter must define:

```text
current generated representation
+
model output
→
next GenerativeState
```

Do not fake unavailable sensory detail.

If a model only supports:

```text
action → opaque outcome
```

then the next generated state must remain correspondingly sparse.

---

## Tests

```text
test_rollout.py

test_rollout_depth.py

test_rollout_budget.py

test_rollout_uncertainty.py

test_rollout_determinism.py
```

Must test:

```text
depth 0
depth 1
depth N

model unavailable

budget exhaustion

uncertainty does not vanish

same seed → same rollout
```

---

## Experiment

```text
GC-E1 — Multi-step Predictive Utility
```

Compare:

```text
persistence
one-step
multi-step
```

at multiple horizons.

---

## Status

```text
IMPLEMENTED — bounded substrate only
```

The engine enforces workspace depth, state, transition and model-query bounds, deterministic proposal selection, and monotonic uncertainty propagation. Focused unit coverage exists for multi-step composition. Runtime wiring, budget-exhaustion/model-unavailable cases, determinism coverage, and GC-E1 scientific evidence remain open.

---

# 7. GC-4 — Branching

## Spec

Relevant:

```text
§56–58
```

## Current code

A bounded `BranchEngine` now creates sibling generated states from one parent using deterministic model ordering and the workspace branch budget. Prospective Agency still evaluates multiple candidate actions independently, but that remains:

```text
parallel one-step candidate evaluation
```

not:

```text
branching generative trajectories
```

---

## Remaining implementation

Implemented in:

```text
branch.py
```

with:

```text
BranchEngine
```

Still required:

```text
branch pruning
state equivalence
branch merge
```

Example:

```text
          S0
       /   |   \
      A    B    C
      │    │    │
      A1   B1   C1
```

---

## Reuse

Existing deterministic tie-breaking patterns are available in:

```text
StructuralContention
```

Do not reuse its semantics directly, but its approach to:

```text
stable hashing
deterministic ordering
bounded arbitration
```

is appropriate.

---

## Tests

```text
test_branching.py

test_branch_budget.py

test_branch_deduplication.py

test_branch_merge.py

test_branch_determinism.py
```

---

## Experiment

GC-E2 ultimately measures whether branching adds planning utility.

---

## Status

```text
PARTIAL — bounded sibling branch substrate only
```

---

# 8. GC-5 — Counterfactual cognition

## Spec

Relevant:

```text
§61
§67–69
§115 GC-E3
```

## Current code

This is one of the strongest existing foundations.

Current code already has:

```text
CounterfactualPrediction
```

and:

```python
predict_competence_outcome(...)
```

The latter performs:

```text
active Private SLM
+
current opaque context
+
alternative competence
→
predicted outcome
```

without recording factual experience.

This already respects the central epistemic boundary.

---

## Remaining implementation

The new bounded `CounterfactualEngine` delegates to the rollout substrate and preserves counterfactual origin/operation provenance. Concrete model-owner adapters and equivalence coverage remain open. The existing implementation is narrowly:

```text
action counterfactual
+
one-step
+
Private SLM
```

Generative Cognition requires generic:

```text
state counterfactual

model-assumption counterfactual

relation counterfactual

multi-step consequence
```

within organism-owned representations.

Implemented in:

```text
counterfactual.py
```

---

## Migration

The existing:

```python
predict_competence_outcome()
```

should initially remain.

Add a thin adapter around it.

Later GC-9 may route Prospective Agency through Generative Cognition.

Do not remove the proven one-step route until equivalence tests pass.

---

## Tests

```text
test_counterfactual.py

test_counterfactual_private_slm_adapter.py

test_counterfactual_provenance.py
```

---

## Experiment

```text
GC-E3 — Counterfactual Utility
```

---

## Status

```text
PARTIAL — bounded generic substrate only
```

One-step motor counterfactual cognition is already real, and a generic bounded counterfactual rollout path now exists. Concrete state/model/relation adapters, runtime routing, equivalence tests and GC-E3 utility evidence remain open.

---

# 9. GC-6 — Episodic replay

## Spec

Relevant:

```text
§59–60
§120 GC-E8
```

## Current code

Substantial substrate exists in:

```text
src/symbiont/modeling/episodic.py
```

Existing:

```text
EpisodicProjection

EpisodeStep

ExperienceEpisode

EpisodicExperienceMemory
```

The episodic representation is already:

```text
bounded
organism-native
semantics-free
provenance-aware
```

Important existing invariant:

```text
EpisodeStep
rejects SourceKind.MODEL
```

and episodic memory only accepts causal factual observations through `_is_causal_observation()`.

This is ideal for GC.

There are also existing replay-related study types such as:

```text
CognitiveReplay
```

and adaptive replay studies.

---

## Missing

What is absent is:

```text
factual episode
        ↓
GenerativeEpisode(origin=REPLAYED)
```

Implement:

```text
replay.py
```

as an adapter over existing episodic storage.

Replay must copy:

```text
projection
provenance
source ids
```

but not:

```text
factual authority
```

---

## Important invariant

Replay must never call:

```text
record_experience(...)
```

as if a replay were a new causal observation.

---

## Tests

```text
test_replay.py

test_replay_provenance.py

test_replay_no_factual_support.py

test_replay_source_identity.py
```

---

## Experiment

```text
GC-E8 — Replay Utility
```

---

## Status

```text
IMPLEMENTED — bounded materialization only
```

Memory and replay data are largely ready. The generative instantiation now
exists behind an explicit projection boundary; concrete episodic-memory wiring,
replay equivalence and GC-E8 utility evidence remain open.

---

# 10. GC-7 — Recombination

## Spec

Relevant:

```text
§62–64
§116 GC-E4
```

## Current code

`ExperienceRecombiner` now composes two bounded cross-episode fragments only
when they share an organism-owned compatibility key. The result is an
`IMAGINED` state retaining both source episode/state identities. The episodic
representation remains suitable because it already separates:

```text
sense_ids

concept_ids

internal_tokens

action_token

effect_features
```

and bounds each dimension.

This provides an excellent substrate.

---

## Implemented substrate

Implemented in:

```text
recombination.py
```

with:

```text
ExperienceRecombiner
RecombinationFragment
```

Compatibility must use only organism-owned structure:

```text
shared concepts

shared context

learned relations

model compatibility

episodic overlap
```

---

## Avoid

Do not implement:

```text
random token mixing
```

and call it creativity.

---

## Tests

```text
test_recombination.py

test_recombination_compatibility.py

test_recombination_novelty.py

test_recombination_provenance.py
```

---

## Experiment

```text
GC-E4 — Recombination
```

with controlled:

```text
A+B
C+D

never A+D
```

---

## Status

```text
MISSING
```

---

# 11. GC-8 — Hypotheses and reconciliation

## Spec

Relevant:

```text
§65–72
§119 GC-E7
```

## Current code

There is strong conceptual precedent.

`ExperienceRecord` supports:

```text
HYPOTHESIZED

PREDICTED

SUPPORTED

CONTRADICTED

RETIRED
```

Private SLM validation already performs:

```text
prediction
    ↓
real episode
    ↓
SUPPORTED / CONTRADICTED
```

This means the repository already has one narrow form of reconciliation.

---

## Missing

There is no generic:

```text
GenerativeHypothesis
```

that can persist independently of:

```text
ExperienceRecord
```

and accumulate:

```text
source generative episodes

supporting models

factual support refs

factual conflict refs

uncertainty

status
```

Implement:

```text
hypothesis.py
reconciliation.py
calibration.py
```

---

## Important reuse

Do not duplicate factual validation.

Generic reconciliation should ultimately delegate factual comparison to existing evidence-producing mechanisms where possible.

---

## Tests

```text
test_hypothesis.py

test_hypothesis_lifecycle.py

test_reconciliation.py

test_prediction_calibration.py
```

---

## Experiment

```text
GC-E7 — Model Correction
```

Also supports:

```text
GC-E6 — Depth Calibration
```

---

## Status

```text
PARTIAL — bounded lifecycle and reconciliation substrate
```

The narrow prediction-validation pattern still exists, and the generic
hypothesis lifecycle, explicit reconciliation boundary and bounded calibration
statistics now exist. Durable persistence, runtime integration and GC-E6/GC-E7
evidence remain open.

---

# 12. GC-9 — Epistemic Agency

## Spec

Relevant:

```text
§67–69
```

## Current code

Current:

```text
ProspectiveAgency
```

already provides excellent authority separation:

```text
agency chooses

runtime executes

sensorimotor owns skill
```

It also has:

```text
query budget

model confidence

OutcomeValueLedger

abstention
```

However, it currently evaluates primarily:

```text
predicted outcome
+
historically learned endogenous value
```

There is no generic:

```text
EpistemicValue
```

and no hypothesis-discrimination component.

---

## Missing

Implement:

```text
EpistemicValue
```

derived from:

```text
expected uncertainty reduction

hypothesis discrimination

model disagreement
```

Then expose it to Agency.

Do not allow Generative Cognition itself to choose motor actions.

---

## Expected final path

```text
Generative Cognition
        ↓
trajectory / hypothesis discrimination

ProspectiveAgency
        ↓
decision

existing action path
```

---

## Tests

```text
test_epistemic_value.py

test_agency_generative_integration.py

test_agency_retains_execution_boundary.py
```

---

## Experiment

Primary:

```text
GC-E3 — Counterfactual Utility
```

with true hypothesis discrimination.

---

## Status

```text
PARTIAL
```

Pragmatic prospective agency exists.

Epistemic agency does not.

---

# 13. GC-10 — Generative consolidation

## Spec

Relevant:

```text
§73–82
§123–125
```

## Current code

This phase has particularly strong reusable infrastructure.

### `MemoryConsolidator`

Already provides:

```text
bounded candidate buffer

fast/slow consolidation

epoch-separated support

bounded durable state
```

However it is designed for memory consolidation, not generative structural demand.

Do not overload it.

### `RepresentationTracker`

Already tracks:

```text
observation_count

active_count

born_tick

maturity
```

Important problem:

these counts do not currently distinguish:

```text
factual activation

from

generated activation
```

Therefore Generative Cognition must not simply call:

```python
RepresentationTracker.observe(...)
```

for imagined states.

That would mix epistemologies.

### `StructuralContention`

This is especially useful.

It already provides:

```text
producer-neutral structural admission arbitration
```

and allows candidates with:

```text
family

producer_id

mutations

eligible_tick
```

This means Generative Consolidation should likely become:

```text
another structural producer
```

rather than acquiring graph mutation authority.

That aligns almost perfectly with the spec.

### `StructuralPlanner`

Already owns:

```text
one consolidation transaction
```

and should remain final planner.

---

## Missing

Implement:

```text
consolidation.py
```

with:

```text
GenerativeConsolidationSignal
GenerativeConsolidator
```

Fields:

```text
recurrent_activation

cross_episode_reuse

hypothesis_persistence

model_disagreement

generative_demand

independent_episode_count

source_diversity
```

Then translate mature demand into:

```text
StructuralCandidate
```

through the normal contention system.

---

## Critical rule

Generative consolidation must never call:

```text
CognitiveGraph mutation
```

directly.

Correct:

```text
GenerativeConsolidation
        ↓
StructuralCandidate
        ↓
StructuralContention
        ↓
StructuralPlanner
```

---

## Required separation

Do not merge:

```text
RepresentationTracker.observation_count
```

with:

```text
generative reuse count
```

Create a separate generative-use tracker.

---

## Tests

```text
test_generative_consolidation.py

test_consolidation_source_diversity.py

test_cross_episode_vs_within_episode.py

test_consolidation_decay.py

test_structural_candidate_projection.py

test_no_direct_graph_mutation.py
```

Adversarial:

```text
1000 replays
!=
1000 observations

single branch loop
!=
cross-episode reuse

same memory repeatedly replayed
!=
many independent factual sources
```

---

## Experiments

```text
GC-E11 — Generative Consolidation

GC-E12 — Consolidation Contamination

GC-E13 — Agenda × Consolidation Interaction
```

GC-E13 is release-blocking.

---

## Status

```text
PARTIAL
```

The structural admission architecture is ready.

The generative producer is missing.

---

# 14. GC-11 — Offline cognition

## Spec

Relevant:

```text
§40–44
```

## Current code

Searches for offline cognition do not reveal a generative processing mode.

Existing uses of "offline" refer to unrelated concerns such as:

```text
offline exchange
temporal policy
```

There is no:

```text
GenerativeMode.ONLINE
GenerativeMode.IDLE
GenerativeMode.OFFLINE
```

---

## Missing

Implement Scheduler modes.

Likely:

```text
scheduler.py
```

with:

```text
GenerativeMode

mode-specific budgets

opportunity detection
```

The first implementation should remain deterministic and synchronous.

Do not introduce threads.

---

## Runtime integration

Recommended:

```text
CognitionDomain
        ↓
Generative service
```

rather than adding algorithms into `OrganismRuntime`.

`CognitionDomain` already has a clean responsibility:

```text
run cognition and sensory learning
without owning physical action
```

Generative cognition naturally fits beneath it.

---

## Tests

```text
test_scheduler.py

test_online_budget.py

test_idle_mode.py

test_offline_mode.py

test_offline_no_world_mutation.py
```

---

## Scientific experiment

Replay and consolidation experiments should compare:

```text
ONLINE only

ONLINE + IDLE

ONLINE + OFFLINE
```

with identical factual experience.

---

## Status

```text
MISSING
```

---

# 15. GC-12 — Observatory / Cognitive Atlas

## Spec

Relevant:

```text
§95–100
```

## Current code

This is another strong foundation.

Existing:

```text
src/symbiont_lab/observation/projection.py

src/symbiont_lab/observation/atlas.py
```

Atlas v2 is explicitly:

```text
deterministic

read-only

observer-derived

presentation-only

non-feedback
```

The recent commits have also made the canonical Atlas projection the live source for the Mind UI.

Existing browser code already handles:

```text
snapshot ingestion

Atlas topology

timeline

history

diff

inspector

live activity
```

So observer infrastructure is not a blocker.

---

## Missing

No current projection contains:

```text
generative agenda

active generative episode

generated states

generated transitions

branches

hypotheses

reconciliation

consolidation

factual contamination

agenda contamination
```

---

## Implementation

Extend organism-side passive snapshot with bounded:

```text
generative
```

projection.

Then extend:

```text
observation/projection.py
```

and Atlas classification.

Possible new Atlas node/edge kinds:

```text
generative_state

generative_hypothesis

generative_target
```

but ephemeral states must remain visually and semantically distinct from canonical learned graph nodes.

---

## Important boundary

Do not put generative ephemeral state directly into:

```text
CognitiveGraph
```

just to make Atlas display it.

Atlas already understands multiple sources.

Use that capability.

---

## Tests

Python:

```text
test_generative_projection.py

test_atlas_generative_layer.py

test_observer_no_feedback.py
```

Frontend:

```text
generative snapshot ingestion

factual/generated visual distinction

branch lifecycle

target selection lifecycle

terminated state cleanup
```

---

## Experiment

Observer validation rather than scientific cognitive proof:

```text
same organism run
with Observatory enabled/disabled
→ identical organism future
```

---

## Status

```text
PARTIAL
```

Observer architecture is mature.

Generative data does not yet exist.

---

# 16. Exact SPEC → code → gap → test → experiment matrix

| GC | Spec | Current code | Missing implementation | Core tests | Experiment |
|---|---|---|---|---|---|
| **GC-0** | §§9–28, 90–94, 107–110 | `modeling/experience.py`, `agency/types.py`, `private_runtime.py` | Generative provenance model, workspace, firewall, schema | provenance + firewall + persistence | **GC-E5** |
| **GC-1** | §§29–38, 111 | autonomous-training pattern only | Agenda, targets, progress/stagnation, contamination guard | agenda autonomy + anti-rumination | **GC-E10** |
| **GC-2** | §§46–50 | Private SLM, sensorimotor models, competence-effect model | GenerativeModel protocol + registry + adapters | adapter-equivalence | prerequisite GC-E1 |
| **GC-3** | §§51–55 | one-step prediction only | RolloutEngine | depth/budget/uncertainty/determinism | **GC-E1** |
| **GC-4** | §§56–58 | independent one-step candidates | branch tree, pruning, equivalence | branch bounds + merge | **GC-E2** |
| **GC-5** | §61 | `CounterfactualPrediction`, `predict_competence_outcome()` | generic multi-state counterfactual | provenance + intervention | **GC-E3** |
| **GC-6** | §§59–60 | `EpisodicExperienceMemory`, `EpisodicProjection` | replay → GenerativeEpisode | no factual duplication | **GC-E8** |
| **GC-7** | §§62–64 | episodic fragments available | recombination engine | compatibility + novelty | **GC-E4** |
| **GC-8** | §§65–72 | PREDICTED/SUPPORTED/CONTRADICTED validation | durable hypotheses + generic reconciliation + calibration | lifecycle + later reality | **GC-E6/E7** |
| **GC-9** | §§67–69 | `ProspectiveAgency`, `OutcomeValueLedger` | EpistemicValue + discrimination integration | authority boundary | **GC-E3** |
| **GC-10** | §§73–82 | `MemoryConsolidator`, `StructuralContention`, `StructuralPlanner` | generative-demand tracker + producer | diversity + no self-confirmation | **GC-E11/12/13** |
| **GC-11** | §§40–44 | none | ONLINE/IDLE/OFFLINE Scheduler | scheduling + no-world-mutation | GC-E8 extensions |
| **GC-12** | §§95–100 | Atlas v2 + passive Mind projection | generative projection + UI layer | passive projection | observer invariance |

---

# 17. Recommended new files

The spec's proposed structure still fits `main`.

Create:

```text
src/symbiont/cognition/generative/
│
├── __init__.py
├── types.py
├── epistemic.py
├── state.py
├── transition.py
├── episode.py
│
├── agenda.py
├── scheduler.py
│
├── workspace.py
│
├── model.py
├── registry.py
│
├── budget.py
│
├── rollout.py
├── branching.py
│
├── replay.py
├── counterfactual.py
├── recombination.py
│
├── hypothesis.py
├── reconciliation.py
│
├── consolidation.py
├── calibration.py
│
├── persistence.py
└── projection.py
```

Avoid placing algorithms in:

```text
core/orchestration/runtime.py
```

---

# 18. Existing files that should change

Expected minimal integration surface:

```text
src/symbiont/core/domains/cognition.py

src/symbiont/core/orchestration/runtime.py

src/symbiont/modeling/runtime.py

src/symbiont/modeling/private_runtime.py

src/symbiont/agency/prospective.py

src/symbiont/core/cognition/structural_candidates.py
    possibly no change if existing register API is sufficient

src/symbiont/core/cognition/structural_planner.py
    ideally no generative-specific knowledge

src/symbiont/host/checkpoint.py

src/symbiont_lab/observation/projection.py

src/symbiont_lab/observation/atlas.py

src/symbiont_lab/workbench/web/views/mind/*
```

A good implementation should avoid making:

```text
StructuralPlanner
ProspectiveAgency
Atlas
```

know too much about GC internals.

---

# 19. Runtime integration recommendation

Do not instantiate the algorithms directly in `OrganismRuntime`.

Preferred shape:

```text
OrganismRuntime
      │
      ▼
CognitionDomain
      │
      ▼
GenerativeCognition
      │
      ├── Agenda
      ├── Scheduler
      ├── Workspace
      └── Registry
```

Where:

```text
CognitionDomain
```

coordinates bounded generative work.

This is consistent with Runtime v2.

---

# 20. Modeled runtime issue

One architectural detail needs careful handling.

Private SLM currently exists only in:

```text
ModeledOrganismRuntime
/
PrivateModelOrganismRuntime
```

while Generative Cognition belongs to the general Symbiont.

Therefore:

```text
Generative Cognition
must not depend on PrivateModelOrganismRuntime.
```

Correct direction:

```text
base Generative Cognition
       ↑
model adapter injection
       ↑
PrivateModelOrganismRuntime
```

If no Private SLM exists:

```text
PrivateSLM adapter absent
```

but other generative models may still participate.

This preserves OS/model independence.

---

# 21. Do not destroy the current one-step agency

The existing Prospective Agency path is useful as:

```text
baseline
fallback
regression oracle
```

During GC-0 → GC-8, retain:

```python
predict_competence_outcome()
```

and current:

```text
ProspectiveAgency.deliberate()
```

Then, in GC-9:

```text
old one-step direct predictor
vs
Generative Cognition depth=1
```

must produce equivalent results under equivalent inputs before changing production routing.

Only after that should deeper GC become the canonical prospective input.

---

# 22. Consolidation integration recommendation

Do not extend:

```python
MemoryConsolidator
```

with generative semantics.

Keep two separate concepts:

```text
MemoryConsolidator
    factual/salient memory persistence

GenerativeConsolidator
    evidence of cognitive demand
```

Then converge only at:

```text
StructuralContention
```

Conceptually:

```text
PredictorLifecycle ─────┐
ConceptLifecycle ───────┤
repair/recycling ───────┤
                        ▼
               StructuralContention
                        ▲
                        │
GenerativeConsolidator ─┘
```

This is probably the cleanest existing extension point in the whole GC implementation.

---

# 23. RepresentationTracker warning

Do not reuse:

```python
RepresentationTracker.observe()
```

for generated activation.

Today it increments:

```text
observation_count
active_count
```

Those counters currently imply actual runtime cognitive activation.

Mixing imagined activation into those counters would make:

```text
generated cognition
```

indistinguishable from:

```text
factual cognitive usage
```

Instead create separate:

```text
GenerativeUsageTracker
```

or equivalent.

Only its consolidated output reaches StructuralContention.

---

# 24. Required experimental directory

Suggested:

```text
experiments/learning/generative-cognition/
```

with:

```text
gc-e1-predictive-utility/
gc-e2-planning-utility/
gc-e3-counterfactual-utility/
gc-e4-recombination/
gc-e5-factual-contamination/
gc-e6-depth-calibration/
gc-e7-model-correction/
gc-e8-replay-utility/
gc-e9-reembodiment-transfer/
gc-e10-endogenous-agenda/
gc-e11-generative-consolidation/
gc-e12-consolidation-contamination/
gc-e13-agenda-consolidation-feedback/
gc-e14-cross-domain-generality/
```

E14 can remain deferred.

---

# 25. Release gates

## Technical release gates

Before v1 can be considered technically implemented:

```text
GC-0 → GC-12 code complete

unit tests green

architecture guards green

checkpoint round-trip green

determinism demonstrated

bounded memory demonstrated

observer invariance demonstrated
```

## Scientific release gates

At minimum:

```text
GC-E1
GC-E2
GC-E3
GC-E4
GC-E5
GC-E6
GC-E7
GC-E8
GC-E10
GC-E11
GC-E12
GC-E13
```

must be runnable and reproducible.

Hard invariants:

```text
factual_contamination_count == 0

agenda_contamination_count == 0
```

GC-E13 must demonstrate absence of pathological self-reinforcing cognitive monopoly.

---

# 26. Practical implementation order

I would execute exactly this sequence.

## Wave 1 — safe substrate

```text
GC-0
Epistemic foundation
```

Then:

```text
GC-1
Agenda
```

and:

```text
GC-2
Model adapters
```

These two can proceed almost independently.

---

## Wave 2 — imagination

```text
GC-3
Rollout

GC-4
Branching

GC-5
Counterfactual
```

At the end of this wave:

```text
Symbiont can think forward
```

but cannot yet meaningfully reconstruct and combine its past.

---

## Wave 3 — constructive memory

```text
GC-6
Replay

GC-7
Recombination
```

At the end:

```text
Symbiont can construct possibilities
not directly experienced
```

---

## Wave 4 — scientific thought

```text
GC-8
Hypotheses + reconciliation

GC-9
Epistemic agency
```

At the end:

```text
Symbiont can think

form alternatives

identify distinguishing observations

and ask reality
```

---

## Wave 5 — thinking changes cognition

```text
GC-10
Generative Consolidation
```

At the end:

```text
thinking may change
how Symbiont is structurally organised

without changing factual truth
```

This wave requires particularly aggressive adversarial testing.

---

## Wave 6 — autonomous internal cognition

```text
GC-11
ONLINE / IDLE / OFFLINE
```

This produces the first complete autonomous generative cycle.

---

## Wave 7 — microscope

```text
GC-12
Observatory / Atlas
```

Only after the causal system is canonical should we render it.

Do not design cognition around what is easiest to visualise.

---

# 27. Expected implementation difficulty

Approximate relative complexity:

```text
GC-0    medium
GC-1    medium-high
GC-2    medium
GC-3    high
GC-4    medium-high
GC-5    medium
GC-6    medium
GC-7    high
GC-8    high
GC-9    medium-high
GC-10   very high
GC-11   medium
GC-12   medium
```

The riskiest parts are not rollout.

They are:

```text
GC-1
because autonomy can be faked accidentally

GC-8
because hypotheses can contaminate evidence

GC-10
because internal repetition can self-confirm

GC-13 experiment
because Agenda × Consolidation can create
self-reinforcing cognitive attractors
```

---

# 28. What should not be touched yet

Do not add during this implementation:

```text
abstraction

analogy

mathematics

language

sleep physiology

recursive self-model

new social cognition

new genome loci
```

Generative Cognition v1 needs to prove itself first.

---

# 29. Current-state verdict

The codebase is in a good position to implement the spec.

We do **not** have:

```text
a hidden pre-existing Generative Cognition
that merely needs connecting
```

but we also do **not** need:

```text
a new cognitive architecture from scratch
```

What exists today can be viewed as:

```text
             CURRENT MAIN

Episodic Memory ──────────────┐
                              │
Private SLM ──────────────────┤
                              │
Counterfactual Prediction ────┤
                              │
Prospective Agency ───────────┤
                              │
CognitiveGraph ───────────────┤
                              │
Structural Plasticity ────────┤
                              ▼
                    [ MISSING LAYER ]
                              │
                              ▼
                  Generative Cognition
```

The implementation job is primarily to build that missing compositional layer while preserving the existing authority boundaries.

---

# 30. Final audit result

The frozen spec survives confrontation with `main`.

No major spec rewrite is required.

The implementation should:

```text
REUSE

EpistemicStatus
ExperienceRecord protections
EpisodicExperienceMemory
Private SLM
CounterfactualPrediction
ProspectiveAgency
OutcomeValueLedger
SensorimotorDynamicsModel
CompetenceEffectModel
StructuralContention
StructuralPlanner
Atlas v2
```

and introduce:

```text
NEW

Generative provenance
Workspace

Agenda
Scheduler

Model registry/adapters

Rollout
Branching

Replay adapter
Counterfactual engine
Recombination

Hypotheses
Reconciliation
Calibration

EpistemicValue

GenerativeConsolidation
GenerativeUsageTracker

Generative persistence

Generative passive projection
```

The recommended starting point is therefore unambiguous:

```text
GC-0
```

followed immediately by:

```text
GC-1
+
GC-2
```

before attempting deeper imagination.

The implementation should not start with `RolloutEngine`.

Without GC-0 and GC-1 first, we could successfully implement:

```text
how to imagine
```

while leaving unresolved:

```text
whether imagination is epistemically safe

and

who decides what gets imagined
```

which are the two most important architectural guarantees of Generative Cognition v1.
