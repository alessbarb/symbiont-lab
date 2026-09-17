# v0.57 Label-Free Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add prediction error (Huber loss), eligibility traces, and bounded Oja weight updates as pure functions operating on the v0.56 graph's data structures — demonstrating measurable label-free learning without any runtime wiring yet.

**Architecture:** `PlasticNode` gains `predicts_node_id` (validated at `CognitiveGraph` construction). A new `cognition/learning.py` holds three independent, composable, mutation-scoped functions: `compute_prediction_errors()` (read-only, returns error/loss per predictor), `update_eligibility()` (mutates one edge's `eligibility` in place), `apply_oja_update()` (mutates one edge's `weight` in place, clipped, only when eligible).

**Tech Stack:** Python 3.11+, dataclasses, `math`, pytest. No new dependencies.

**Spec:** `docs/_internal/specs/2026-09-14-v057-label-free-learning-design.md` — read both together. Master design: `docs/design/endogenous-plasticity.md` §6.1-§6.3.

## Global Constraints

- No metaplasticity, no composite Pareto objective, no structural mutation — v0.58 (spec §2).
- No wiring into `OrganismRuntime`'s tick loop — `learning_rate` and `modulation` stay plain caller-supplied floats this slice (spec §2, §4.3).
- `apply_oja_update()` is a no-op when `eligible=False` (spec §4.3, master doc §6.3).
- Edge weight stays within `WEIGHT_RANGE` (`-2.0, 2.0`) after every Oja update, even under adversarial repeated calls.
- `PlasticNode.predicts_node_id` is required (non-`None`, referencing a declared node) iff `kind is NodeKind.PREDICTOR`, and forbidden otherwise (spec §3, §4.4).

---

## Task 1: `predicts_node_id` and graph validation

**Files:**
- Modify: `src/symbiont/cognition/graph.py`
- Test: `tests/unit/cognition/test_graph.py`

**Interfaces:**
- Produces: `PlasticNode.predicts_node_id: str | None = None` (new field, default `None` so every existing `PlasticNode(...)` call site from v0.55/v0.56 stays valid unchanged).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_graph.py (append)
def test_predictor_node_without_predicts_node_id_is_rejected():
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(predictor,), edges=(), kernel_limits=KernelLimits())


def test_predictor_node_with_dangling_predicts_node_id_is_rejected():
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR, predicts_node_id="ghost")
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(predictor,), edges=(), kernel_limits=KernelLimits())


def test_non_predictor_node_with_predicts_node_id_is_rejected():
    bad_concept = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT, predicts_node_id="c1")
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(bad_concept,), edges=(), kernel_limits=KernelLimits())


def test_valid_predictor_node_constructs_successfully():
    target = _concept_node("target")
    predictor = PlasticNode(node_id="p1", kind=NodeKind.PREDICTOR, predicts_node_id="target")
    CognitiveGraph(nodes=(target, predictor), edges=(), kernel_limits=KernelLimits())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_graph.py -v -k predicts_node_id`
Expected: FAIL — `TypeError: PlasticNode.__init__() got an unexpected keyword argument 'predicts_node_id'`.

- [ ] **Step 3: Write minimal implementation**

In `src/symbiont/cognition/graph.py`, add the field:

```python
@dataclass(slots=True, frozen=True)
class PlasticNode:
    node_id: str
    kind: NodeKind
    bias: float = 0.0
    tau: float = 1.0
    predicts_node_id: str | None = None
```

In `CognitiveGraph.__init__`, after the existing per-node loop that populates `self._nodes_by_id` (so every node id is already known), add a second pass validating `predicts_node_id`:

```python
        for node in self._nodes_by_id.values():
            if node.kind is NodeKind.PREDICTOR:
                if node.predicts_node_id is None:
                    raise GraphError(f"PREDICTOR node {node.node_id!r} must set predicts_node_id")
                if node.predicts_node_id not in self._nodes_by_id:
                    raise GraphError(
                        f"PREDICTOR node {node.node_id!r} predicts_node_id "
                        f"{node.predicts_node_id!r} is not a declared node"
                    )
            elif node.predicts_node_id is not None:
                raise GraphError(f"non-PREDICTOR node {node.node_id!r} must not set predicts_node_id")
```

(place this loop right after the existing node-registration loop, before the
node/edge count checks — order relative to the count checks doesn't matter
functionally, but keeping all node-level validation together keeps the
method readable.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_graph.py -v`
Expected: PASS, all tests including every pre-existing v0.56 test (default `predicts_node_id=None` keeps every old `PlasticNode(...)` call valid).

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/graph.py tests/unit/cognition/test_graph.py
git commit -m "$(cat <<'EOF'
feat(cognition): add PlasticNode.predicts_node_id and validation

A PREDICTOR node must declare which node's future activation it
predicts (disclosed doc gap -- the master doc's node table doesn't
specify this). Required and must reference a declared node for
PREDICTOR nodes, forbidden for every other kind. Defaults to None so
every existing v0.55/v0.56 PlasticNode call site is unaffected.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: Prediction error (`cognition/learning.py`)

**Files:**
- Create: `src/symbiont/cognition/learning.py`
- Test: `tests/unit/cognition/test_learning.py`

**Interfaces:**
- Consumes: `CognitiveGraph`, `PlasticNode`, `NodeKind` (v0.55/v0.56), `PlasticNode.predicts_node_id` (Task 1).
- Produces: `huber_loss(error: float, delta: float = 1.0) -> float`, `PredictionError` (frozen dataclass: `predictor_id`, `target_id`, `error`, `loss`), `compute_prediction_errors(graph: CognitiveGraph, *, current: Mapping[str, float], previous: Mapping[str, float]) -> tuple[PredictionError, ...]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_learning.py
from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.learning import PredictionError, compute_prediction_errors, huber_loss
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind


def _target(node_id: str = "target") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def _predictor(node_id: str = "p1", predicts: str = "target") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.PREDICTOR, predicts_node_id=predicts)


def test_huber_loss_is_quadratic_within_delta():
    assert huber_loss(0.5, delta=1.0) == pytest.approx(0.5 * 0.5 * 0.5)


def test_huber_loss_is_linear_beyond_delta():
    assert huber_loss(2.0, delta=1.0) == pytest.approx(1.0 * (2.0 - 0.5))


def test_huber_loss_is_zero_at_zero_error():
    assert huber_loss(0.0) == 0.0


def test_huber_loss_is_symmetric():
    assert huber_loss(1.5) == pytest.approx(huber_loss(-1.5))


def test_exact_prediction_yields_zero_error():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.3, "p1": 0.1}, previous={"target": 0.0, "p1": 0.3})
    assert len(errors) == 1
    assert errors[0] == PredictionError(predictor_id="p1", target_id="target", error=0.0, loss=0.0)


def test_mismatched_prediction_yields_nonzero_error():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.8, "p1": 0.1}, previous={"target": 0.0, "p1": 0.1})
    assert errors[0].error == pytest.approx(0.7)
    assert errors[0].loss > 0.0


def test_cold_start_predictor_missing_from_previous_is_skipped():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.5}, previous={})
    assert errors == ()


def test_multiple_predictors_are_returned_sorted_by_predictor_id():
    nodes = (_target(), _predictor("p2"), _predictor("p1"))
    graph = CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(
        graph, current={"target": 0.5, "p1": 0.0, "p2": 0.0}, previous={"target": 0.0, "p1": 0.0, "p2": 0.0}
    )
    assert [error.predictor_id for error in errors] == ["p1", "p2"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_learning.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.learning'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/learning.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .graph import CognitiveGraph
from .types import NodeKind


def huber_loss(error: float, delta: float = 1.0) -> float:
    magnitude = abs(error)
    if magnitude <= delta:
        return 0.5 * error * error
    return delta * (magnitude - 0.5 * delta)


@dataclass(slots=True, frozen=True)
class PredictionError:
    predictor_id: str
    target_id: str
    error: float
    loss: float


def compute_prediction_errors(
    graph: CognitiveGraph, *, current: Mapping[str, float], previous: Mapping[str, float]
) -> tuple[PredictionError, ...]:
    predictors = sorted(
        (node for node in graph.nodes if node.kind is NodeKind.PREDICTOR), key=lambda node: node.node_id
    )
    errors: list[PredictionError] = []
    for predictor in predictors:
        if predictor.node_id not in previous:
            continue  # cold start: no prediction was made last tick
        target_id = predictor.predicts_node_id
        assert target_id is not None  # guaranteed by CognitiveGraph construction validation
        target_value = current.get(target_id, 0.0)
        predicted_value = previous[predictor.node_id]
        error = target_value - predicted_value
        errors.append(
            PredictionError(predictor_id=predictor.node_id, target_id=target_id, error=error, loss=huber_loss(error))
        )
    return tuple(errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_learning.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/learning.py tests/unit/cognition/test_learning.py
git commit -m "$(cat <<'EOF'
feat(cognition): add prediction error via Huber loss

compute_prediction_errors() compares each PREDICTOR node's previous-
tick activation (its prediction) against its declared target's
current activation, through a Huber loss (quadratic near zero, linear
beyond delta -- robust to outlier surprises). A predictor absent from
the previous frame (cold start) is skipped rather than reported as a
spurious large error.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 3: Eligibility trace and bounded Oja weight update

**Files:**
- Modify: `src/symbiont/cognition/learning.py`
- Test: `tests/unit/cognition/test_learning.py`

**Interfaces:**
- Consumes: `PlasticEdge` (v0.56), `WEIGHT_RANGE` (v0.55 `types.py`).
- Produces: `update_eligibility(edge: PlasticEdge, *, source_previous: float, target_current: float, decay: float) -> None`, `apply_oja_update(edge: PlasticEdge, *, source_activation: float, target_activation: float, learning_rate: float, modulation: float, eligible: bool) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_learning.py (append)
from symbiont.cognition.graph import PlasticEdge
from symbiont.cognition.learning import apply_oja_update, update_eligibility
from symbiont.cognition.types import EdgeKind, WEIGHT_RANGE


def _edge(weight: float = 0.5) -> PlasticEdge:
    return PlasticEdge(
        source_id="a", target_id="b", kind=EdgeKind.EXCITATORY, weight=weight, plasticity=0.5, delay_ticks=1
    )


def test_eligibility_grows_with_sustained_coactivation():
    edge = _edge()
    for _ in range(20):
        update_eligibility(edge, source_previous=0.8, target_current=0.8, decay=0.9)
    assert edge.eligibility > 0.5


def test_eligibility_decays_toward_zero_without_coactivation():
    edge = _edge()
    edge.eligibility = 1.0
    for _ in range(50):
        update_eligibility(edge, source_previous=0.0, target_current=0.0, decay=0.9)
    assert abs(edge.eligibility) < 0.01


def test_eligibility_stays_finite_and_bounded_under_repeated_extremes():
    import math

    edge = _edge()
    for _ in range(1000):
        update_eligibility(edge, source_previous=1.0, target_current=1.0, decay=0.99)
    assert math.isfinite(edge.eligibility)
    assert abs(edge.eligibility) <= 1.0 / (1.0 - 0.99) + 1e-6


def test_oja_update_is_a_noop_when_not_eligible():
    edge = _edge(weight=0.5)
    apply_oja_update(edge, source_activation=1.0, target_activation=1.0, learning_rate=0.5, modulation=1.0, eligible=False)
    assert edge.weight == 0.5


def test_oja_update_is_a_noop_when_modulation_is_zero():
    edge = _edge(weight=0.5)
    apply_oja_update(edge, source_activation=1.0, target_activation=1.0, learning_rate=0.5, modulation=0.0, eligible=True)
    assert edge.weight == 0.5


def test_oja_update_moves_weight_toward_correlated_activity():
    edge = _edge(weight=0.1)
    for _ in range(50):
        apply_oja_update(
            edge, source_activation=0.9, target_activation=0.9, learning_rate=0.1, modulation=1.0, eligible=True
        )
    assert edge.weight > 0.1


def test_oja_update_never_leaves_weight_range_under_repeated_extremes():
    edge = _edge(weight=0.0)
    for _ in range(2000):
        apply_oja_update(
            edge, source_activation=1.0, target_activation=1.0, learning_rate=0.9, modulation=1.0, eligible=True
        )
    assert WEIGHT_RANGE[0] <= edge.weight <= WEIGHT_RANGE[1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_learning.py -v -k "eligibility or oja"`
Expected: FAIL — `ImportError: cannot import name 'apply_oja_update'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/learning.py`:

```python
from .types import WEIGHT_RANGE
```

```python
def update_eligibility(edge: "PlasticEdge", *, source_previous: float, target_current: float, decay: float) -> None:
    edge.eligibility = decay * edge.eligibility + source_previous * target_current


def apply_oja_update(
    edge: "PlasticEdge",
    *,
    source_activation: float,
    target_activation: float,
    learning_rate: float,
    modulation: float,
    eligible: bool,
) -> None:
    if not eligible or modulation == 0.0:
        return
    delta = learning_rate * modulation * (
        source_activation * target_activation - target_activation * target_activation * edge.weight
    )
    new_weight = edge.weight + delta
    edge.weight = max(WEIGHT_RANGE[0], min(WEIGHT_RANGE[1], new_weight))
```

Add the `PlasticEdge` import at the top (needed for the type hints used
above — quoted in the signatures only because `PlasticEdge` is imported
alongside `CognitiveGraph` from `.graph`, avoid a duplicate import line by
extending the existing one):

```python
from .graph import CognitiveGraph, PlasticEdge
```

(then drop the quotes around `"PlasticEdge"` in both new function
signatures, since it's now a real import, not a forward reference.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_learning.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/learning.py tests/unit/cognition/test_learning.py
git commit -m "$(cat <<'EOF'
feat(cognition): add eligibility traces and bounded Oja weight update

update_eligibility() mutates an edge's eligibility via a decaying
pre/post-synaptic coincidence trace. apply_oja_update() mutates an
edge's weight via a bounded Oja rule, clipped to WEIGHT_RANGE after
every update -- a no-op when the edge isn't eligible (master doc
§6.3: only edges within the causal window and selected by attention
get a full update) or when modulation is zero (a fully-suppressed
tick). learning_rate and modulation stay plain caller-supplied floats
this slice -- no metaplasticity or SelfModel wiring yet (v0.58+).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: End-to-end learning demonstration

**Files:**
- Test: `tests/unit/cognition/test_learning.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3, plus `CognitiveGraph.activate()` (v0.56).

- [ ] **Step 1: Write the failing test**

```python
def test_a_predictor_measurably_learns_a_periodic_signal_over_many_ticks():
    from symbiont.cognition.graph import TickContext

    sense = PlasticNode(node_id="s", kind=NodeKind.SENSE)
    predictor = PlasticNode(node_id="p", kind=NodeKind.PREDICTOR, predicts_node_id="s", bias=0.0, tau=1.0)
    feed = PlasticEdge(source_id="s", target_id="p", kind=EdgeKind.PREDICTIVE, weight=0.05, plasticity=0.5, delay_ticks=0)
    graph = CognitiveGraph(nodes=(sense, predictor), edges=(feed,), kernel_limits=KernelLimits())

    previous_frame: dict[str, float] = {}
    losses: list[float] = []
    for tick in range(1, 201):
        signal = 0.8 if tick % 2 == 0 else -0.8
        frame = graph.activate(inputs={"s": signal}, context=TickContext(tick=tick), previous=previous_frame)

        errors = compute_prediction_errors(graph, current=frame.activations, previous=previous_frame)
        for error in errors:
            update_eligibility(feed, source_previous=previous_frame.get("s", 0.0), target_current=frame.activations["p"], decay=0.9)
            apply_oja_update(
                feed,
                source_activation=previous_frame.get("s", 0.0),
                target_activation=frame.activations["p"],
                learning_rate=0.05,
                modulation=1.0,
                eligible=True,
            )
            losses.append(error.loss)

        previous_frame = dict(frame.activations)

    early_average = sum(losses[:20]) / 20
    late_average = sum(losses[-20:]) / 20
    assert late_average < early_average
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cognition/test_learning.py -v -k measurably_learns`
Expected: This test exercises only already-implemented functions from
Tasks 1-3, so it should already PASS once those tasks are done — this
step is a demonstration/regression guard, not new-feature-driven TDD. Run
it anyway to confirm the loss genuinely trends down with the exact
learning-rate/decay constants chosen; if it does not converge, adjust
`learning_rate`/`decay`/tick count (not the underlying `apply_oja_update`/
`update_eligibility` implementations, which Task 3 already tested
independently) until it does, since a flat or diverging loss here would
mean the demonstration itself is miscalibrated, not that the learning
primitives are broken.

- [ ] **Step 3: N/A — demonstration test only, no new implementation expected**

- [ ] **Step 4: Run the full suite**

Run: `pytest -q`
Expected: every test in the repository passes.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/cognition/test_learning.py
git commit -m "$(cat <<'EOF'
test(cognition): demonstrate measurable label-free learning

An end-to-end loop (activate -> compute_prediction_errors ->
update_eligibility -> apply_oja_update, repeated 200 ticks against a
periodic sense signal) shows PredictionError.loss trending down --
closing out the roadmap's own bar for this milestone ("demostrará
aprendizaje de pesos").

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**
- §4.1 prediction error / Huber loss → Task 2.
- §4.2 eligibility trace → Task 3.
- §4.3 bounded Oja update → Task 3.
- §4.4 `predicts_node_id` + graph validation → Task 1.
- §5's end-to-end demonstration bullet → Task 4.
- Non-goals (§2): no task adds metaplasticity, Pareto objective, structural mutation, or `OrganismRuntime` wiring.

**Type consistency check:** `PredictionError` fields (`predictor_id`, `target_id`, `error`, `loss`) from Task 2 match Task 4's usage exactly. `update_eligibility`/`apply_oja_update` signatures from Task 3 are used identically in Task 4's end-to-end loop. `PlasticNode.predicts_node_id` (Task 1) is the field `compute_prediction_errors` (Task 2) reads via `predictor.predicts_node_id`.
