# CognitiveBridge decomposition design

## Context

`src/symbiont/core/cognition/bridge.py` defines `CognitiveBridge`, a
single class of 3,545 lines and roughly 94 methods (~14 public, ~80
private). It is the one remaining monolith in the cognition/orchestration
layer: recent work already decomposed `OrganismRuntime`'s tick pipeline
into explicit domain objects (`PerceptionDomain`, `CognitionDomain`,
`ActionDomain`, etc. — see `src/symbiont/core/domains/`) and removed
`OrganismRuntime`'s dead/redundant compatibility properties (commits
`b60b2964`, `4c2d5a6b`, `8d3167be`). `CognitiveBridge` was untouched by
that work and is now the largest concentration of responsibility left
in the codebase.

`CognitiveBridge` owns, on a single flat `self`, six largely
independent concerns: Oja plasticity/weight consolidation, predictor
utility/retirement/shadow-prediction lifecycle, sense admission/
eviction, concept birth/recycling, structural mutation/contention, and
checkpoint export/restore. `CognitionDomain.step()` — its only caller
inside the domain-orchestration layer — uses just 4 of its ~14 public
members (`tick`, `nominate_shadow_prediction`, `shadow_predictions`,
`graph`); the rest of the public API is consumed piecemeal by
`OrganismRuntime`, `DevelopmentDomain`, `RegulationDomain`,
`ActionDomain`, and `symbiont.modeling.runtime`/`private_runtime`.

The repository already has a precedent for splitting primitive/math
logic out of orchestration code: `src/symbiont/cognition/structure.py`,
`learning.py`, and `checkpoint.py` hold the data model and math that
`bridge.py` calls into. No equivalent split exists yet for `bridge.py`'s
own *decision* logic (candidate selection, contention, retirement,
lifecycle bookkeeping) — this design proposes that split.

**Goal:** reduce `CognitiveBridge` to a thin coordinator (target
~500-700 lines) with identical public API and identical observable
behavior, by extracting five collaborator components that each own a
cohesive slice of the current state and logic. This is a pure
structural refactor — no algorithm, no learning behavior, and no
mutation ordering changes.

**Out of scope:** any change to what the bridge computes, to
`cognition/{structure,learning,checkpoint,graph,activation,
metaplasticity,types,limits}.py` (unchanged, still imported as-is), or
to `CognitionDomain`'s external contract with `CognitiveBridge`.

## Architecture

`CognitiveBridge` retains only the state and behavior that is
genuinely cross-cutting or shared by every collaborator:

- Core identity state: `self._graph` (`CognitiveGraph`),
  `self._topology_revision`, `self._tick`, `self._safety_state`.
- Error handling: the try/except around `graph.activate()` and the
  freeze-after-3-consecutive-errors rule. This stays centralized in
  `CognitiveBridge.tick()` — no collaborator introduces its own
  try/except; each collaborator propagates exceptions instead of
  swallowing them.
- The full existing public API, kept at identical signatures, each
  method now a thin delegator to the relevant collaborator (or to
  `graph`/`safety_state` directly, unchanged).

**Safety invariant governing the whole design:** collaborators never
hold a back-reference to `CognitiveBridge` or to each other. They
receive `graph`/`tick` (and any other needed scalars) as **method
arguments**, never stored as instance attributes pointing outward.
Instead of mutating `self._graph` directly, every collaborator that
currently proposes structural changes returns `Mutation` objects (the
existing primitive type from `cognition/structure.py`).
`CognitiveBridge.tick()` remains the single place that calls
`graph.apply_mutations(...)`, and does so in the same relative order
the current monolithic `tick()` executes its steps in today. This
refactor moves *where* logic lives; it does not reorder *when* it
runs. Mutation-ordering/contention rules are safety-critical (they
determine which of two competing structural proposals wins in a given
tick) and today are implicit in call order inside one function — after
this refactor they become explicit in `StructuralContention
.select_and_commit()`, called from one point in `tick()`.

## Components

All five live under `src/symbiont/core/cognition/`, alongside the
existing `structure.py`/`learning.py`/`checkpoint.py` (which they call
into, unchanged).

### 1. `PlasticityEngine` (`plasticity_state.py`)

Smallest, most self-contained cluster. Owns: `_normalizers`,
`_previous_frame`, `_weight_tracker`, `_tracked_edge_keys`.

Methods: `apply_oja_update(graph, tick)`, `consolidate_weights(graph)`.
Both call into the existing `cognition/learning.py` primitives
unchanged.

### 2. `PredictorLifecycle` (`predictors.py`)

Owns: `_predictor_utility`, `_predictor_retirement`,
`_shadow_predictions` (+ cache/dirty flags), `_shadow_preliminary_support`.

Methods: `record_prediction_errors(errors, tick)`,
`retire_due(graph, tick) -> list[Mutation]`,
`nominate_shadow(graph, tick)`, `promote_shadow(shadow_id, graph)`.
Property: `shadow_predictions`.

### 3. `SenseConceptLifecycle` (`sense_concept_lifecycle.py`)

Owns sense admission/eviction: `_sense_last_seen_tick`,
`_adaptive_sense_budget`, `_develop_senses`. Owns concept birth/
recycling: `_concept_support`, `_retrospective_concept_support`,
`_concept_lineage`, `_orphan_since_tick`, `_unrouted_since_tick`,
`_concept_last_active_tick`, `_next_concept_index`, concept-signature
caches.

Methods: `admit_senses(graph, tick) -> list[Mutation]`,
`propose_concept_recycling(graph, tick) -> list[Mutation]`,
`observe_retrospective_support(...)`.
Properties: `stranded_concepts`, `concept_lineage`.

### 4. `StructuralContention` (`structural_candidates.py`)

The hub. Owns: `_structural_candidates`, `_contention_identity`,
`_last_consolidated_producer_id`, `_consolidation_generation`,
`_adaptive_node_budget`, `_adaptive_edge_budget`, topology-health
caches.

Central method: `select_and_commit(candidates: list[Mutation], graph,
tick) -> list[Mutation]` — applies the existing contention/priority/
budget rules (today scattered across `_register_structural_candidate`,
`_select_structural_candidate`, `_commit_contention_result`,
`_valid_candidate`, `_prune_invalid_structural_proposals`, etc.) in one
place. `PredictorLifecycle`, `SenseConceptLifecycle`, and
`PlasticityEngine`-adjacent logic (motor/primitive readout sync,
representation maturity, motor association evidence) *propose*
candidates here; none of them apply mutations directly.

### 5. `CheckpointComposer` (`bridge_checkpoint.py`)

Plain module-level functions, not a class — it has no state that
persists between ticks, only work to do at save/restore time.

- `export_bridge_state(plasticity, predictors, lifecycle, contention,
  graph, safety_state) -> dict`
- `restore_bridge_state(payload) -> tuple[PlasticityEngine,
  PredictorLifecycle, SenseConceptLifecycle, StructuralContention]`

Composes the existing lower-level codec functions in
`cognition/checkpoint.py` (graph/safety-state/sensory-normalizer
export/restore — unchanged) plus new serialization for the four
collaborators' own dicts, replacing the ~15 private `_restore_*`
helpers currently on `CognitiveBridge`.

### `CognitiveBridge` after decomposition

Retains `__init__` (constructs the five collaborators and the core
state), all read-only status accessor properties (`graph`,
`safety_state`, `topology_revision`, `develop_senses`,
`recovery_pending`, `concept_lineage`, `unrouted_since_tick`,
`next_concept_index`, `topology_health`), `set_expression_state`,
`expression_state`, `bind_contention_identity`, and thin delegators for
`tick`, `export_checkpoint`, `restore`, `observe_primitive_execution`,
`observe_homeostatic_action_outcome`, `observe_retrospective_support`,
`shadow_predictions`, `promote_shadow_prediction`,
`nominate_shadow_prediction`, `stranded_concepts`. Every one of these
keeps its current signature and return type — this is why the 15+
existing test files and 6 external call sites (`OrganismRuntime`,
`DevelopmentDomain`, `RegulationDomain`, `ActionDomain`,
`symbiont.modeling.{runtime,private_runtime}`) require no changes.

## Data flow (`tick()`)

Same step order as today; only *who* executes each step changes.

```
1.  sync motor/primitive readouts          -> mutations (stays inline in bridge; small)
2.  topology recovery check                -> bridge + StructuralContention (reads/writes topology_revision + safety_state)
3.  normalize senses                       -> learning.py (unchanged)
4.  graph.activate()                       -> CognitiveGraph (unchanged)
5.  prediction errors                      -> learning.py (unchanged) -> PredictorLifecycle.record_prediction_errors(...)
6.  predictor retirement                   -> PredictorLifecycle.retire_due(...) -> candidates
7.  Oja plasticity / weight consolidation  -> PlasticityEngine.apply_oja_update(...) / consolidate_weights(...)
8.  representation maturity / coactivation -> SenseConceptLifecycle -> candidates
9.  motor association evidence             -> StructuralContention -> candidates
10. concept support / sense admission      -> SenseConceptLifecycle.admit_senses(...) -> candidates
11. shadow prediction learning             -> PredictorLifecycle -> candidates
12. StructuralContention.select_and_commit(candidates from 6-11) -> final Mutation list, same order/dedup as today
13. graph.apply_mutations(mutations)       -> topology_revision bump
14. GC / retirement / pruning / concept recycling -> SenseConceptLifecycle + StructuralContention (post-mutation, same tick)
15. return CognitiveBridgeResult           -> shape unchanged
```

Steps 6-11 mutate the graph directly today, scattered through the
current `tick()` body in call order. After this refactor each of those
steps *returns* candidates instead, and step 12 consumes them in that
same relative order — the contention rule (which of two competing
proposals wins when they touch the same node/edge in one tick) is
unchanged, only made explicit in one call instead of implicit in
method-call sequence. This is the most delicate part of the migration:
it must be validated against a line-by-line diff of the current
`tick()` body before any collaborator extraction begins, not designed
from scratch.

## Error handling

No behavior change. The freeze-after-3-consecutive-graph-errors rule
and the try/except around `graph.activate()` stay on `CognitiveBridge`
itself — this is cross-cutting safety state, not owned by any one
collaborator. Collaborators raise on invariant violations rather than
catching; `CognitiveBridge.tick()` remains the single catch point, as
it is today.

## Testing

**Migration order** (least to most entangled, matching the current
state-ownership analysis): `PlasticityEngine` → `PredictorLifecycle` →
`SenseConceptLifecycle` → `StructuralContention` → `CheckpointComposer`
(last, since it serializes the other four's state and needs them to
exist first).

**Safety net:** `tests/unit/core/test_cognition_bridge.py` (17 tests)
plus ~10 more files that construct `CognitiveBridge` directly and
exercise its public API (`test_reversible_structure_phase2/3/4.py`,
`test_shadow_promotion.py`, `test_concept_recycling.py`,
`test_adversarial_hardening.py`, `test_semantic_bootstrap_aliasing.py`,
`test_concept_support_consumption.py`, `test_generic_internal_
retirement.py`, `test_resident_continuity.py`,
`test_representation_maturity.py`, `test_structural_contention.py`,
`test_failed_concept_reclamation.py`,
`test_reversible_structural_plasticity.py`,
`tests/unit/genetics/test_genome_v2.py`) are all behavior tests
through the public API, not implementation tests. If the public API
and observable behavior are unchanged, they pass unmodified. Run the
full set after **every** phase, not just at the end — same discipline
used for the `OrganismRuntime` shim-removal slices (identical
pass/fail set required before moving to the next phase).

**New tests:** one per collaborator, exercising it in isolation
against a plain `CognitiveGraph` fixture, asserting observable
behavior (candidates proposed, properties exposed) rather than private
state — per this repo's existing testing convention (`CLAUDE.md`:
"assertions about public repertoire, selection, recurrence... unless
private state itself is the documented contract").

## Migration phases (for the implementation plan)

1. `PlasticityEngine` extraction + verification.
2. `PredictorLifecycle` extraction + verification.
3. `SenseConceptLifecycle` extraction + verification.
4. `StructuralContention` extraction (the hub — highest risk, requires
   the line-by-line mutation-order diff described above) + verification.
5. `CheckpointComposer` extraction + verification.
6. Final pass: confirm `CognitiveBridge` line count, run the complete
   affected-test set once more, `graphify update .`.

Each phase is independently committable and independently revertible.
No phase changes `CognitiveBridge`'s public API.
