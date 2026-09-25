# CognitiveBridge decomposition — Phase 2 design

## Status

Planned follow-up after the first decomposition lands on `main`.

The first phase reduces the original `CognitiveBridge` monolith into explicit collaborators while preserving the public API and the established tick ordering. Phase 2 is intentionally separate: it must begin from a merged, characterized baseline rather than continuing an open-ended extraction.

## Baseline after Phase 1

The bridge is no longer the sole owner of cognition. The following responsibilities now have explicit homes:

- `PlasticityEngine`: edge-local learning, eligibility, Oja updates, reversible retirement decay, edge ageing, durable weight consolidation and homeostatic weight modulation.
- `PredictorLifecycle`: predictor utility, retirement/quarantine, shadow hypotheses, pruning, nomination and promotion proposals.
- `SenseConceptLifecycle`: sensory/concept developmental bookkeeping, support, lineage, routing, orphaning and recycling.
- `RepresentationTracker`: representation birth, observation/activity evidence and maturity.
- `StructuralContention`: structural candidate registry, producer fairness and arbitration.
- `StructuralPlanner`: pre-activation structural synchronization plus the sequential consolidation planning transaction.
- `bridge_checkpoint.py`: durable checkpoint export/restore codecs.
- `bridge_compat.py`: temporary private compatibility surface for tests and studies.

The live graph still follows the important transaction rule:

```text
live graph
  -> sequential planning graph
  -> maintenance
  -> repair
  -> admission/contention
  -> generic growth
  -> complete ordered mutation batch
  -> atomic graph commit
```

Later planning stages see the provisional graph produced by earlier stages, but partial topology is not published.

## Why Phase 2 is separate

Phase 1 is a structural refactor. Several remaining improvements either widen the behavioral surface or require stronger characterization before they are safe.

The next work must therefore not be framed as "keep shrinking bridge.py". The goal is to finish ownership boundaries without moving semantics accidentally.

## Adversarial invariants carried into Phase 2

Phase 2 must preserve the following characterized behavior:

1. **Terminal structural failure rolls back the complete graph transaction.**
   Earlier maintenance staged in the planning graph must not leak into the live graph if the final ordered mutation batch is rejected.

2. **Checkpoint restore is a durable-state fixed point.**
   For a valid checkpoint, `restore(export(state)).export()` must reproduce the durable payload.

3. **Primitive retraction is pre-activation behavior.**
   A materialized primitive readout that is no longer active is removed before graph activation for that tick.

4. **Same-tick planning visibility remains sequential.**
   A later maintenance phase may observe topology produced provisionally by an earlier phase in the same consolidation tick.

5. **Public `CognitiveBridge` API remains stable until callers are deliberately migrated.**

## Known inherited semantic gap: topology atomicity is not full cognition atomicity

The consolidation transaction is atomic for `CognitiveGraph`, but planning currently mutates some non-graph state before the final commit, including parts of:

- structural candidate registry,
- consolidation generation,
- unrouted tracking,
- adaptive budgets,
- recycling-event staging.

Therefore a final graph commit can fail after some planning bookkeeping has already changed.

This behavior predates the decomposition. Phase 1 must not silently change it.

Phase 2 must decide explicitly between two contracts:

### Option A — preserve topology-only atomicity

Document that only graph publication is transactional and that planner bookkeeping is allowed to advance on a failed graph transaction.

### Option B — introduce cognition-transaction atomicity

Stage all mutable planner/lifecycle/contention/budget state beside the planning graph and publish all of it only when the final transaction commits.

Option B is architecturally cleaner, but it is a behavior change and requires its own tests and migration decision.

## Target architecture

### 1. Keep CognitiveBridge as the temporal coordinator

`CognitiveBridge` should continue owning the things that are truly tick orchestration:

- current live graph reference,
- current tick,
- previous activation frame,
- sensory normalizers,
- safety state,
- gene-expression snapshot,
- topology revision,
- recovery/reacclimation gate,
- activation error boundary,
- collaborator ordering,
- final `CognitiveBridgeResult` publication.

A target size of roughly 700–900 lines is a guide, not an acceptance criterion.

### 2. Split StructuralPlanner by responsibility

The current planner contains both surface synchronization and consolidation planning.

Extract:

```text
StructuralSurfaceLifecycle
    sync_motor_readouts
    sync_primitive_readouts
    admit_senses
```

Keep:

```text
StructuralPlanner
    retirement GC
    edge pruning
    orphan GC
    sense eviction staging
    repair staging
    admission/contention staging
    generic growth staging
    final transaction candidate
```

Action-association evidence should not become another unrelated responsibility of `StructuralPlanner`. It should either remain with the structural learning model or move to a small dedicated collaborator.

### 3. Finish SenseConceptLifecycle boundaries

The current combined lifecycle is an acceptable Phase-1 extraction but not necessarily the final shape.

Natural later boundaries are:

```text
SensoryLifecycle
    last-seen state
    retention/eviction policy

ConceptLifecycle
    support
    retrospective support
    signatures
    lineage
    birth
    orphan/routing/recycling
```

`RepresentationTracker` remains independent and generic.

Do not split these classes until characterization demonstrates the current combined behavior.

### 4. Remove cross-component reconciliation from CognitiveBridge

Today `_record_applied_metadata()` and `_reconcile_node_metadata()` still know the internals of several collaborators.

Replace that with explicit ownership hooks or a narrow reconciler, for example:

```python
representations.apply_mutations(...)
lifecycle.apply_mutations(...)
predictors.apply_mutations(...)
plasticity.reconcile_graph(...)
```

The bridge may sequence reconciliation, but should not know the dictionaries each collaborator must clean.

### 5. Retire bridge_compat.py

`bridge_compat.py` is a migration scaffold, not permanent architecture.

Migration order:

1. inventory every private bridge reference in tests and studies;
2. move component-specific tests to the owning collaborator;
3. expose a narrow public/testing API only where a real external contract exists;
4. migrate studies away from private bridge methods;
5. delete compatibility properties/methods once no callers remain.

Do not make the compatibility mixin the long-term API.

### 6. Separate result projection if it remains large

The final section of `tick()` constructs a broad telemetry/result projection. If it remains a significant fraction of the coordinator, extract a passive `CognitiveResultProjector`.

It must receive state and return a result; it must never mutate cognition.

## Differential characterization before every Phase-2 extraction

Phase 2 should add scenario-level characterization, not only isolated unit tests.

For each scenario, record or compare tick-by-tick:

- result fields,
- graph nodes and edges,
- weight/eligibility/support state,
- predictor utility and retirement,
- shadow hypotheses,
- concept support and lineage,
- orphan/unrouted state,
- structural candidates and producer cursor,
- adaptive budgets,
- topology revision,
- recovery state,
- checkpoint payload.

Required scenarios:

- stable learning without structural growth,
- sense admission,
- primitive appearance/disappearance,
- motor readout admission,
- predictor promotion/retirement,
- concept birth,
- prune -> orphan same-tick visibility,
- recycling,
- capacity pressure,
- terminal structural rejection,
- checkpoint -> restore,
- re-embodiment/reacclimation.

## Phase-2 implementation order

### Wave 0 — characterization

- preserve the Phase-1 adversarial tests;
- add scenario snapshots/differential fixtures;
- inventory private compatibility callers;
- document the chosen atomicity contract.

### Wave 1 — structural surface boundary

- extract `StructuralSurfaceLifecycle`;
- preserve pre-activation ordering exactly;
- keep `StructuralPlanner` focused on consolidation.

### Wave 2 — reconciliation ownership

- move mutation metadata/reconcile rules into owners;
- remove direct dictionary surgery from `CognitiveBridge`.

### Wave 3 — lifecycle refinement

- evaluate `SensoryLifecycle` / `ConceptLifecycle` split;
- perform only if the characterization suite stays invariant.

### Wave 4 — compatibility retirement

- migrate tests and studies;
- delete obsolete private proxies.

### Wave 5 — coordinator cleanup

- extract passive result projection if still justified;
- remove dead imports/constants/helpers;
- document the final public contract.

## Acceptance criteria

Phase 2 is complete only when:

- `CognitiveBridge` contains orchestration rather than domain algorithms;
- no collaborator holds a back-reference to the bridge;
- structural planning preserves sequential planning visibility;
- graph commit semantics are explicitly tested;
- the chosen non-graph atomicity contract is documented and tested;
- checkpoint round-trip invariants remain intact;
- private compatibility has been eliminated or reduced to explicitly justified cases;
- tests/studies depend on owning components rather than bridge internals;
- no behavior change is hidden inside a structural commit.

## Non-goals

Phase 2 must not redesign:

- cognitive learning policy,
- concept semantics,
- predictor utility criteria,
- structural fairness policy,
- genome parameters,
- embodiment semantics,
- motor learning policy.

Any such change requires a separate behavioral specification.
