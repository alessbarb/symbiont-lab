# v0.58 Metaplasticity and Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the composite Pareto objective, bounded/revertible metaplasticity, structural edge/concept creation, the pruning lifecycle, and a safe-mode state tracker — five standalone mechanisms extending the v0.56/v0.57 graph, no runtime wiring yet.

**Architecture:** `cognition/metaplasticity.py` holds the objective vector, `MetaParameter`, and `SafetyState` — small, independent dataclasses with no dependency on the graph. `cognition/structure.py` holds everything that changes graph topology: `Mutation`/`ValidationResult`, `StructuralPlasticity` (tracks co-activation, proposes new edges), `validate_mutation`/`apply_mutations` (rebuild a new `CognitiveGraph` via its existing validated constructor rather than mutating topology in place), `propose_concept`, and the pure `evaluate_edge_lifecycle` pruning function.

**Tech Stack:** Python 3.11+, dataclasses, `enum.StrEnum`, `random`, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-14-v058-metaplasticity-and-structure-design.md` — read both together. Master design: `docs/design/endogenous-plasticity.md` §6.4-§6.5, §7, §13.

## Global Constraints

- No `OrganismRuntime` wiring — standalone toolkit, matching v0.56/v0.57 precedent (spec §1, §2).
- `CognitiveGraph` stays immutable; structural mutation rebuilds a new graph via its existing constructor (spec §2, §3.3).
- `dominates()` is Pareto dominance, never a weighted sum (spec §3.1).
- `MetaParameter.propose()` only commits a delta when the current-window objective is not dominated by the previous (spec §3.2).
- `evaluate_edge_lifecycle()` is a pure function — no side effects, no stored lifecycle state (spec §3.5).
- `SafetyState.frozen` never clears without an explicit `reset()` call (spec §3.6).

---

## Task 1: Composite objective and Pareto dominance (`cognition/metaplasticity.py`)

**Files:**
- Create: `src/symbiont/cognition/metaplasticity.py`
- Test: `tests/unit/cognition/test_metaplasticity.py`

**Interfaces:**
- Produces: `LearningObjective` (frozen dataclass: `prediction_error`, `representation_cost`, `instability`, `information_retained`, `calibration`), `dominates(a: LearningObjective, b: LearningObjective) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_metaplasticity.py
from __future__ import annotations

from symbiont.cognition.metaplasticity import LearningObjective, dominates


def _objective(
    prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5
) -> LearningObjective:
    return LearningObjective(
        prediction_error=prediction_error,
        representation_cost=representation_cost,
        instability=instability,
        information_retained=information_retained,
        calibration=calibration,
    )


def test_identical_objectives_never_dominate_each_other():
    a = _objective()
    b = _objective()
    assert not dominates(a, b)
    assert not dominates(b, a)


def test_strictly_better_on_all_dimensions_dominates():
    better = _objective(
        prediction_error=0.1, representation_cost=0.1, instability=0.1, information_retained=0.9, calibration=0.9
    )
    worse = _objective(
        prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5
    )
    assert dominates(better, worse)
    assert not dominates(worse, better)


def test_mixed_improvement_and_regression_dominates_neither_way():
    mixed = _objective(prediction_error=0.1, representation_cost=0.9)  # better on one, worse on another
    baseline = _objective(prediction_error=0.5, representation_cost=0.5)
    assert not dominates(mixed, baseline)
    assert not dominates(baseline, mixed)


def test_better_on_one_dimension_equal_on_rest_dominates():
    better = _objective(prediction_error=0.1)
    baseline = _objective(prediction_error=0.5)
    assert dominates(better, baseline)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_metaplasticity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.metaplasticity'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/metaplasticity.py
from __future__ import annotations

from dataclasses import dataclass

_LOWER_IS_BETTER = ("prediction_error", "representation_cost", "instability")
_HIGHER_IS_BETTER = ("information_retained", "calibration")


@dataclass(slots=True, frozen=True)
class LearningObjective:
    prediction_error: float
    representation_cost: float
    instability: float
    information_retained: float
    calibration: float


def dominates(a: LearningObjective, b: LearningObjective) -> bool:
    at_least_as_good = True
    strictly_better_somewhere = False
    for field in _LOWER_IS_BETTER:
        a_value, b_value = getattr(a, field), getattr(b, field)
        if a_value > b_value:
            at_least_as_good = False
        elif a_value < b_value:
            strictly_better_somewhere = True
    for field in _HIGHER_IS_BETTER:
        a_value, b_value = getattr(a, field), getattr(b, field)
        if a_value < b_value:
            at_least_as_good = False
        elif a_value > b_value:
            strictly_better_somewhere = True
    return at_least_as_good and strictly_better_somewhere
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_metaplasticity.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/metaplasticity.py tests/unit/cognition/test_metaplasticity.py
git commit -m "$(cat <<'EOF'
feat(cognition): add composite learning objective with Pareto dominance

LearningObjective is a five-dimension observable vector (prediction
error, representation cost, instability, information retained,
calibration); dominates() is standard Pareto dominance -- at least as
good on every dimension, strictly better on at least one. Never a
weighted sum: master doc §6.4 explicitly rejects a single hidden
global objective that could justify unbounded growth.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: `MetaParameter` and `SafetyState`

**Files:**
- Modify: `src/symbiont/cognition/metaplasticity.py`
- Test: `tests/unit/cognition/test_metaplasticity.py`

**Interfaces:**
- Consumes: `LearningObjective`, `dominates` (Task 1).
- Produces: `MetaParameter` (mutable dataclass: `value`, `minimum`, `maximum`, `max_step`, method `propose(*, candidate_delta, previous_window_objective, current_window_objective) -> None`), `SafetyState` (mutable dataclass: `consecutive_failures: int = 0`, `frozen: bool = False`, methods `record_success()`, `record_failure()`, `reset()`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_metaplasticity.py (append)
from symbiont.cognition.metaplasticity import MetaParameter, SafetyState


def test_meta_parameter_commits_delta_when_current_dominates_previous():
    param = MetaParameter(value=0.5, minimum=0.0, maximum=1.0, max_step=0.1)
    previous = _objective(prediction_error=0.5)
    current = _objective(prediction_error=0.1)  # strictly better
    param.propose(candidate_delta=0.05, previous_window_objective=previous, current_window_objective=current)
    assert param.value == 0.55


def test_meta_parameter_commits_delta_when_neither_dominates_tie():
    param = MetaParameter(value=0.5, minimum=0.0, maximum=1.0, max_step=0.1)
    same = _objective()
    param.propose(candidate_delta=0.05, previous_window_objective=same, current_window_objective=same)
    assert param.value == 0.55


def test_meta_parameter_reverts_when_previous_dominates_current():
    param = MetaParameter(value=0.5, minimum=0.0, maximum=1.0, max_step=0.1)
    previous = _objective(prediction_error=0.1)  # previous was better
    current = _objective(prediction_error=0.5)  # current is worse
    param.propose(candidate_delta=0.05, previous_window_objective=previous, current_window_objective=current)
    assert param.value == 0.5


def test_meta_parameter_clips_delta_to_max_step():
    param = MetaParameter(value=0.5, minimum=0.0, maximum=1.0, max_step=0.1)
    same = _objective()
    param.propose(candidate_delta=10.0, previous_window_objective=same, current_window_objective=same)
    assert param.value == 0.6


def test_meta_parameter_never_leaves_its_range():
    param = MetaParameter(value=0.95, minimum=0.0, maximum=1.0, max_step=0.5)
    same = _objective()
    param.propose(candidate_delta=1.0, previous_window_objective=same, current_window_objective=same)
    assert param.value == 1.0


def test_safety_state_freezes_after_three_consecutive_failures():
    state = SafetyState()
    state.record_failure()
    state.record_failure()
    assert not state.frozen
    state.record_failure()
    assert state.frozen


def test_safety_state_success_resets_the_streak():
    state = SafetyState()
    state.record_failure()
    state.record_failure()
    state.record_success()
    state.record_failure()
    state.record_failure()
    assert not state.frozen  # only 2 consecutive since the reset


def test_safety_state_frozen_never_clears_without_explicit_reset():
    state = SafetyState()
    for _ in range(3):
        state.record_failure()
    assert state.frozen
    state.record_success()
    assert state.frozen  # success alone does not unfreeze
    state.reset()
    assert not state.frozen
    assert state.consecutive_failures == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_metaplasticity.py -v -k "meta_parameter or safety_state"`
Expected: FAIL — `ImportError: cannot import name 'MetaParameter'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/metaplasticity.py`:

```python
@dataclass(slots=True)
class MetaParameter:
    value: float
    minimum: float
    maximum: float
    max_step: float

    def propose(
        self,
        *,
        candidate_delta: float,
        previous_window_objective: LearningObjective,
        current_window_objective: LearningObjective,
    ) -> None:
        if dominates(previous_window_objective, current_window_objective):
            return  # things got worse -- never commit
        clipped_delta = max(-self.max_step, min(self.max_step, candidate_delta))
        self.value = max(self.minimum, min(self.maximum, self.value + clipped_delta))


@dataclass(slots=True)
class SafetyState:
    consecutive_failures: int = 0
    frozen: bool = False

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.frozen = True

    def reset(self) -> None:
        self.consecutive_failures = 0
        self.frozen = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_metaplasticity.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/metaplasticity.py tests/unit/cognition/test_metaplasticity.py
git commit -m "$(cat <<'EOF'
feat(cognition): add MetaParameter and SafetyState

MetaParameter.propose() commits a candidate delta (clipped to
max_step, then to [minimum, maximum]) only when the current-window
objective is not dominated by the previous window -- master doc
§6.5's "revert if it got worse," simplified to "only commit if not
worse" (net-equivalent, no speculative-apply-then-undo state needed).
SafetyState freezes after 3 consecutive failures (§13 invariant 9);
success resets the streak but never auto-unfreezes -- only an
explicit reset() clears frozen (invariant 8: fail visibly, never
silently recover).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 3: `StructuralPlasticity` — co-activation tracking and edge proposals

**Files:**
- Create: `src/symbiont/cognition/structure.py`
- Test: `tests/unit/cognition/test_structure.py`

**Interfaces:**
- Consumes: `CognitiveGraph`, `PlasticNode`, `PlasticEdge` (v0.56); `KernelLimits` (v0.55); `EdgeKind` (v0.55).
- Produces: `Mutation` (frozen dataclass: `kind: Literal["add_edge", "add_node", "quarantine_edge", "remove_edge"]`, `payload: Mapping[str, object]`), `StructuralPlasticity.__init__(*, min_candidate_support, tentative_lifetime_ticks, cooldown_ticks)`, `.observe_coactivation(*, source_id, target_id, source_active, target_active, tick)`, `.propose(graph, *, kernel_limits, tick) -> tuple[Mutation, ...]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_structure.py
from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation, StructuralPlasticity
from symbiont.cognition.types import NodeKind


def _sense(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept(node_id: str) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def test_no_proposal_before_minimum_support_reached():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=5, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(4):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=4)
    assert mutations == ()


def test_proposal_fires_once_minimum_support_reached():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(mutations) == 1
    assert mutations[0].kind == "add_edge"
    assert mutations[0].payload["source_id"] == "a"
    assert mutations[0].payload["target_id"] == "b"


def test_no_coactivation_never_reaches_support():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(10):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=False, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=10)
    assert mutations == ()


def test_already_connected_pair_is_never_reproposed():
    from symbiont.cognition.graph import PlasticEdge
    from symbiont.cognition.types import EdgeKind

    existing = PlasticEdge(source_id="a", target_id="b", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0)
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(existing,), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(5):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=5)
    assert mutations == ()


def test_proposal_withheld_when_kernel_edge_budget_exhausted():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    mutations = plasticity.propose(graph, kernel_limits=KernelLimits(max_edges=0), tick=3)
    assert mutations == ()


def test_pair_on_cooldown_after_a_proposal_is_not_reproposed_immediately():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b"), _concept("c")), edges=(), kernel_limits=KernelLimits())
    plasticity = StructuralPlasticity(min_candidate_support=3, tentative_lifetime_ticks=100, cooldown_ticks=10)
    for tick in range(3):
        plasticity.observe_coactivation(source_id="a", target_id="b", source_active=True, target_active=True, tick=tick)
    first = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=3)
    assert len(first) == 1

    for tick in range(3, 6):
        plasticity.observe_coactivation(source_id="a", target_id="c", source_active=True, target_active=True, tick=tick)
    second = plasticity.propose(graph, kernel_limits=KernelLimits(), tick=6)
    assert second == ()  # node "a" is still on cooldown from the first proposal
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_structure.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.structure'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/structure.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from .graph import CognitiveGraph
from .limits import KernelLimits
from .types import EdgeKind

_TENTATIVE_INITIAL_WEIGHT = 0.05

MutationKind = Literal["add_edge", "add_node", "quarantine_edge", "remove_edge"]


@dataclass(slots=True, frozen=True)
class Mutation:
    kind: MutationKind
    payload: Mapping[str, object]


class StructuralPlasticity:
    def __init__(self, *, min_candidate_support: int, tentative_lifetime_ticks: int, cooldown_ticks: int) -> None:
        if min_candidate_support < 1:
            raise ValueError("min_candidate_support must be at least 1")
        if tentative_lifetime_ticks < 1:
            raise ValueError("tentative_lifetime_ticks must be at least 1")
        if cooldown_ticks < 0:
            raise ValueError("cooldown_ticks must be non-negative")
        self._min_candidate_support = min_candidate_support
        self._tentative_lifetime_ticks = tentative_lifetime_ticks
        self._cooldown_ticks = cooldown_ticks
        self._coactivation_counts: dict[tuple[str, str], int] = {}
        self._cooldown_until: dict[str, int] = {}

    def observe_coactivation(
        self, *, source_id: str, target_id: str, source_active: bool, target_active: bool, tick: int
    ) -> None:
        if source_active and target_active:
            key = (source_id, target_id)
            self._coactivation_counts[key] = self._coactivation_counts.get(key, 0) + 1

    def propose(self, graph: CognitiveGraph, *, kernel_limits: KernelLimits, tick: int) -> tuple[Mutation, ...]:
        existing_pairs = {(edge.source_id, edge.target_id) for edge in graph.edges}
        node_ids = {node.node_id for node in graph.nodes}
        mutations: list[Mutation] = []

        for (source_id, target_id), count in sorted(self._coactivation_counts.items()):
            if count < self._min_candidate_support:
                continue
            if source_id not in node_ids or target_id not in node_ids:
                continue
            if (source_id, target_id) in existing_pairs:
                continue
            if len(graph.edges) + len(mutations) >= kernel_limits.max_edges:
                continue
            if self._cooldown_until.get(source_id, -1) >= tick or self._cooldown_until.get(target_id, -1) >= tick:
                continue

            mutations.append(
                Mutation(
                    kind="add_edge",
                    payload={
                        "source_id": source_id,
                        "target_id": target_id,
                        "kind": EdgeKind.EXCITATORY,
                        "weight": _TENTATIVE_INITIAL_WEIGHT,
                        "plasticity": 0.5,
                        "delay_ticks": 1,
                    },
                )
            )
            self._cooldown_until[source_id] = tick + self._cooldown_ticks
            self._cooldown_until[target_id] = tick + self._cooldown_ticks

        return tuple(mutations)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_structure.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/structure.py tests/unit/cognition/test_structure.py
git commit -m "$(cat <<'EOF'
feat(cognition): add StructuralPlasticity edge-creation proposals

Tracks per-pair co-activation counts; once a pair reaches
min_candidate_support it proposes a tentative EXCITATORY add_edge
Mutation (small initial weight, delay=1 since a structurally-created
edge's source is never assumed to be a SENSE node) -- unless the pair
is already connected, the kernel's edge budget is exhausted, or
either endpoint is still on cooldown from a recent proposal. Mutations
are proposals only; nothing here touches the graph.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: `validate_mutation` and `apply_mutations`

**Files:**
- Modify: `src/symbiont/cognition/structure.py`
- Test: `tests/unit/cognition/test_structure.py`

**Interfaces:**
- Consumes: `Mutation`, `CognitiveGraph`, `KernelLimits` (Task 3 / v0.55/v0.56).
- Produces: `ValidationResult` (frozen dataclass: `accepted: bool`, `reason: str | None = None`), `validate_mutation(mutation: Mutation, graph: CognitiveGraph, kernel_limits: KernelLimits) -> ValidationResult`, `apply_mutations(graph: CognitiveGraph, mutations: tuple[Mutation, ...], kernel_limits: KernelLimits) -> CognitiveGraph`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_structure.py (append)
from symbiont.cognition.graph import GraphError, PlasticEdge
from symbiont.cognition.structure import ValidationResult, apply_mutations, validate_mutation
from symbiont.cognition.types import EdgeKind


def _add_edge_mutation(source: str, target: str) -> Mutation:
    return Mutation(
        kind="add_edge",
        payload={
            "source_id": source,
            "target_id": target,
            "kind": EdgeKind.EXCITATORY,
            "weight": 0.05,
            "plasticity": 0.5,
            "delay_ticks": 1,
        },
    )


def test_validate_mutation_accepts_a_sound_add_edge():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_add_edge_mutation("a", "b"), graph, KernelLimits())
    assert result == ValidationResult(accepted=True)


def test_validate_mutation_rejects_when_edge_budget_full():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_add_edge_mutation("a", "b"), graph, KernelLimits(max_edges=0))
    assert not result.accepted
    assert result.reason is not None


def test_validate_mutation_rejects_dangling_endpoint():
    graph = CognitiveGraph(nodes=(_sense("a"),), edges=(), kernel_limits=KernelLimits())
    result = validate_mutation(_add_edge_mutation("a", "ghost"), graph, KernelLimits())
    assert not result.accepted


def test_apply_mutations_produces_a_new_graph_containing_the_edge():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "b"),), KernelLimits())
    assert len(new_graph.edges) == 1
    assert new_graph.edges[0].source_id == "a"
    assert new_graph.edges[0].target_id == "b"
    assert len(graph.edges) == 0  # original graph is untouched


def test_apply_mutations_silently_skips_a_rejected_mutation():
    graph = CognitiveGraph(nodes=(_sense("a"), _concept("b")), edges=(), kernel_limits=KernelLimits())
    new_graph = apply_mutations(graph, (_add_edge_mutation("a", "ghost"),), KernelLimits())
    assert len(new_graph.edges) == 0
    assert len(new_graph.nodes) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_structure.py -v -k "validate_mutation or apply_mutations"`
Expected: FAIL — `ImportError: cannot import name 'ValidationResult'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/structure.py`:

```python
from .graph import GraphError, PlasticEdge, PlasticNode


@dataclass(slots=True, frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None = None


def validate_mutation(mutation: Mutation, graph: CognitiveGraph, kernel_limits: KernelLimits) -> ValidationResult:
    if mutation.kind != "add_edge":
        return ValidationResult(accepted=False, reason=f"unsupported mutation kind {mutation.kind!r} in this version")

    node_ids = {node.node_id for node in graph.nodes}
    source_id = mutation.payload["source_id"]
    target_id = mutation.payload["target_id"]
    if source_id not in node_ids:
        return ValidationResult(accepted=False, reason=f"source {source_id!r} is not a declared node")
    if target_id not in node_ids:
        return ValidationResult(accepted=False, reason=f"target {target_id!r} is not a declared node")
    if len(graph.edges) >= kernel_limits.max_edges:
        return ValidationResult(accepted=False, reason="kernel edge budget exhausted")
    return ValidationResult(accepted=True)


def apply_mutations(
    graph: CognitiveGraph, mutations: tuple[Mutation, ...], kernel_limits: KernelLimits
) -> CognitiveGraph:
    nodes = list(graph.nodes)
    edges = list(graph.edges)

    for mutation in mutations:
        result = validate_mutation(mutation, CognitiveGraph(nodes=tuple(nodes), edges=tuple(edges), kernel_limits=kernel_limits), kernel_limits)
        if not result.accepted:
            continue
        if mutation.kind == "add_edge":
            edges.append(
                PlasticEdge(
                    source_id=mutation.payload["source_id"],
                    target_id=mutation.payload["target_id"],
                    kind=mutation.payload["kind"],
                    weight=mutation.payload["weight"],
                    plasticity=mutation.payload["plasticity"],
                    delay_ticks=mutation.payload["delay_ticks"],
                )
            )

    return CognitiveGraph(nodes=tuple(nodes), edges=tuple(edges), kernel_limits=kernel_limits)
```

(`GraphError`/`PlasticNode` are imported for type-consistency with the
rest of the module and future mutation kinds; only `PlasticEdge` is
actually constructed in this task's `add_edge` branch.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_structure.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/structure.py tests/unit/cognition/test_structure.py
git commit -m "$(cat <<'EOF'
feat(cognition): add validate_mutation and apply_mutations

validate_mutation() checks a proposed mutation against the current
graph and KernelLimits before it is ever applied. apply_mutations()
rebuilds a new CognitiveGraph from the accepted mutations via the
existing validated constructor -- the original graph is never
mutated in place, and a rejected mutation is silently skipped rather
than raising, since a caller applying a batch of proposals expects
partial acceptance to be normal, not exceptional.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 5: Concept creation

**Files:**
- Modify: `src/symbiont/cognition/structure.py`
- Test: `tests/unit/cognition/test_structure.py`

**Interfaces:**
- Consumes: `CognitiveGraph`, `KernelLimits`, `Mutation` (Tasks 3-4 / v0.55/v0.56).
- Produces: `propose_concept(candidate_node_ids: tuple[str, ...], *, graph: CognitiveGraph, kernel_limits: KernelLimits, rng: random.Random) -> Mutation | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_structure.py (append)
import random

from symbiont.cognition.structure import propose_concept


def test_propose_concept_rejects_too_few_candidates():
    graph = CognitiveGraph(nodes=(_sense("a"),), edges=(), kernel_limits=KernelLimits())
    assert propose_concept(("a",), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)) is None


def test_propose_concept_rejects_too_many_candidates():
    nodes = tuple(_sense(f"n{i}") for i in range(5))
    graph = CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits())
    ids = tuple(node.node_id for node in nodes)
    assert propose_concept(ids, graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)) is None


def test_propose_concept_rejects_unknown_node_id():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    assert propose_concept(("a", "ghost"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1)) is None


def test_propose_concept_rejects_when_concept_budget_exhausted():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b"), _concept("c")), edges=(), kernel_limits=KernelLimits())
    result = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(max_concepts=1), rng=random.Random(1))
    assert result is None


def test_propose_concept_returns_an_add_node_mutation_with_opaque_id():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    mutation = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1))
    assert mutation is not None
    assert mutation.kind == "add_node"
    assert mutation.payload["node_id"].startswith("concept_")
    assert mutation.payload["node_id"] not in ("a", "b")


def test_propose_concept_is_deterministic_for_the_same_seed():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    first = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(42))
    second = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(42))
    assert first.payload["node_id"] == second.payload["node_id"]


def test_propose_concept_different_seeds_yield_different_ids():
    graph = CognitiveGraph(nodes=(_sense("a"), _sense("b")), edges=(), kernel_limits=KernelLimits())
    first = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(1))
    second = propose_concept(("a", "b"), graph=graph, kernel_limits=KernelLimits(), rng=random.Random(2))
    assert first.payload["node_id"] != second.payload["node_id"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_structure.py -v -k propose_concept`
Expected: FAIL — `ImportError: cannot import name 'propose_concept'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/structure.py`:

```python
import random

from .types import NodeKind
```

```python
def propose_concept(
    candidate_node_ids: tuple[str, ...],
    *,
    graph: CognitiveGraph,
    kernel_limits: KernelLimits,
    rng: random.Random,
) -> Mutation | None:
    if not (2 <= len(candidate_node_ids) <= 4):
        return None
    node_ids = {node.node_id for node in graph.nodes}
    if not all(candidate_id in node_ids for candidate_id in candidate_node_ids):
        return None
    concept_count = sum(1 for node in graph.nodes if node.kind is NodeKind.CONCEPT)
    if concept_count >= kernel_limits.max_concepts:
        return None

    new_concept_id = f"concept_{rng.getrandbits(64):016x}"
    return Mutation(
        kind="add_node",
        payload={
            "node_id": new_concept_id,
            "kind": NodeKind.CONCEPT,
            "source_ids": candidate_node_ids,
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_structure.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/structure.py tests/unit/cognition/test_structure.py
git commit -m "$(cat <<'EOF'
feat(cognition): add concept creation mechanics

propose_concept() handles only the creation mechanics once a caller
has already identified a 2-4 node stable co-varying cluster --
clustering/co-variance detection is a caller concern (master doc §7.2
describes what a concept IS, not a specific detection algorithm). The
new CONCEPT node's id is an rng-derived opaque token, never derived
from the candidate ids' content, deterministic for a given seed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 6: Pruning lifecycle

**Files:**
- Modify: `src/symbiont/cognition/structure.py`
- Test: `tests/unit/cognition/test_structure.py`

**Interfaces:**
- Consumes: `PlasticEdge` (v0.56).
- Produces: `EdgeLifecycleState` (StrEnum: `ACTIVE`, `WEAK`, `QUARANTINED`, `REMOVED`), `evaluate_edge_lifecycle(edge: PlasticEdge, *, current_tick: int, prune_threshold: float, minimum_support: int, quarantine_window_ticks: int) -> EdgeLifecycleState`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_structure.py (append)
from symbiont.cognition.structure import EdgeLifecycleState, evaluate_edge_lifecycle


def _lifecycle_edge(weight: float, support: int, last_use_tick: int) -> PlasticEdge:
    return PlasticEdge(
        source_id="a", target_id="b", kind=EdgeKind.EXCITATORY, weight=weight, plasticity=0.5, delay_ticks=0,
        support=support, last_use_tick=last_use_tick,
    )


def test_strong_established_edge_is_active():
    edge = _lifecycle_edge(weight=1.5, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(edge, current_tick=10, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.ACTIVE


def test_unestablished_weak_edge_is_still_active_not_yet_judged():
    edge = _lifecycle_edge(weight=0.01, support=2, last_use_tick=10)
    state = evaluate_edge_lifecycle(edge, current_tick=10, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.ACTIVE


def test_established_weak_edge_recently_used_is_weak():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(edge, current_tick=15, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.WEAK


def test_established_weak_edge_stale_past_window_is_quarantined():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(edge, current_tick=61, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.QUARANTINED


def test_quarantined_edge_stale_past_second_window_is_removed():
    edge = _lifecycle_edge(weight=0.01, support=100, last_use_tick=10)
    state = evaluate_edge_lifecycle(edge, current_tick=111, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.REMOVED


def test_edge_that_recovered_weight_returns_to_active():
    edge = _lifecycle_edge(weight=1.0, support=100, last_use_tick=60)
    state = evaluate_edge_lifecycle(edge, current_tick=61, prune_threshold=0.1, minimum_support=16, quarantine_window_ticks=50)
    assert state == EdgeLifecycleState.ACTIVE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_structure.py -v -k lifecycle`
Expected: FAIL — `ImportError: cannot import name 'EdgeLifecycleState'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/structure.py`:

```python
from enum import StrEnum


class EdgeLifecycleState(StrEnum):
    ACTIVE = "active"
    WEAK = "weak"
    QUARANTINED = "quarantined"
    REMOVED = "removed"


def evaluate_edge_lifecycle(
    edge: PlasticEdge,
    *,
    current_tick: int,
    prune_threshold: float,
    minimum_support: int,
    quarantine_window_ticks: int,
) -> EdgeLifecycleState:
    if edge.support < minimum_support:
        return EdgeLifecycleState.ACTIVE  # not established enough to judge yet
    if abs(edge.weight) >= prune_threshold:
        return EdgeLifecycleState.ACTIVE  # weight recovered -- back to normal regardless of staleness

    stale_ticks = current_tick - edge.last_use_tick
    if stale_ticks < quarantine_window_ticks:
        return EdgeLifecycleState.WEAK
    if stale_ticks < 2 * quarantine_window_ticks:
        return EdgeLifecycleState.QUARANTINED
    return EdgeLifecycleState.REMOVED
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_structure.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/structure.py tests/unit/cognition/test_structure.py
git commit -m "$(cat <<'EOF'
feat(cognition): add pruning lifecycle (active/weak/quarantined/removed)

evaluate_edge_lifecycle() is a pure function of an edge's own already-
tracked fields (support, weight, last_use_tick): unestablished edges
stay ACTIVE regardless of weight (not enough evidence to judge yet);
an established edge whose |weight| recovers past prune_threshold
returns to ACTIVE even after going stale -- quarantine is a genuine
recovery window, not a one-way countdown; sustained weakness escalates
WEAK -> QUARANTINED -> REMOVED over two quarantine_window_ticks
windows. Reports state only; a caller decides whether/how to act on
REMOVED via apply_mutations()'s remove_edge kind.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**
- §3.1 composite objective / Pareto dominance → Task 1.
- §3.2 metaplasticity → Task 2.
- §3.6 safe mode → Task 2.
- §3.3 structural edge creation (`StructuralPlasticity`) → Task 3.
- §3.3 `validate_mutation`/`apply_mutations` → Task 4.
- §3.4 concept creation → Task 5.
- §3.5 pruning lifecycle → Task 6.
- Non-goals (§2): no task wires into `OrganismRuntime`; `CognitiveGraph` is never mutated in place, only rebuilt.

**Type consistency check:** `Mutation.kind`/`.payload` (Task 3) match every consumer in Tasks 4-5. `ValidationResult` (Task 4) fields match its use in `apply_mutations`. `EdgeLifecycleState` (Task 6) is self-contained, no cross-task dependency beyond `PlasticEdge`. `KernelLimits.max_edges`/`.max_concepts` (v0.55) are read identically across Tasks 3-5.
