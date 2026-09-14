# v0.56 Cognitive Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a static, deterministic cognitive graph engine — node/edge data structures, sensory normalization, and synchronous double-buffered activation propagation — as a standalone, testable module nothing yet wires into the tick loop.

**Architecture:** `cognition/activation.py` holds a per-sense EWMA normalizer converting raw readings into bounded graph-ready activations. `cognition/graph.py` holds the node/edge dataclasses and `CognitiveGraph`, which validates its topology fully at construction time and computes one synchronous activation pass per `activate()` call, reading only from the caller-supplied `inputs` (this tick's sense activations) and `previous` (last tick's full frame) — never from values computed earlier in the same call, which is what makes the result independent of iteration order.

**Tech Stack:** Python 3.11+, dataclasses, `math`, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-14-v056-cognitive-graph-design.md` — read both together. Master design: `docs/design/endogenous-plasticity.md` §5, §9, §10.

## Global Constraints

- No learning, no eligibility-trace updates, no structural mutation — v0.57/v0.58 (spec §2).
- No genome-driven topology generation — construction is explicit, caller-supplied nodes/edges (spec §1, §6).
- `PlasticEdge` is mutable (`@dataclass(slots=True)`, not frozen), matching the master doc exactly.
- `delay_ticks == 0` is valid only when the edge's source node has `kind == NodeKind.SENSE`; every other source kind must use `delay_ticks == 1` (spec §3.2) — validated at `CognitiveGraph` construction, not at activation time.
- `GATING` edges never contribute directly to `u_j`; they multiply (by product) the contribution of every other edge sharing their target (spec §3.1).
- `TAU_RANGE = (0.1, 10.0)` (spec §4.3).
- Every activation must be `math.isfinite`; a non-finite result raises `GraphError` (spec §4.4 step 5).

---

## Task 1: Sensory normalization (`cognition/activation.py`)

**Files:**
- Modify: `src/symbiont/cognition/types.py` (add `TAU_RANGE`)
- Create: `src/symbiont/cognition/activation.py`
- Test: `tests/unit/cognition/test_activation.py`

**Interfaces:**
- Produces: `TAU_RANGE: tuple[float, float] = (0.1, 10.0)` (in `types.py`); `SensoryNormalizer` with `mean: float`, `variance: float`, `count: int` fields and `normalize(self, raw_value: float, *, z_max: float = 4.0, softness: float = 2.0) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_activation.py
from __future__ import annotations

import math

import pytest

from symbiont.cognition.activation import SensoryNormalizer


def test_cold_start_does_not_divide_by_zero():
    normalizer = SensoryNormalizer()
    result = normalizer.normalize(5.0)
    assert math.isfinite(result)


def test_output_is_always_bounded_by_tanh():
    normalizer = SensoryNormalizer()
    for value in [0.0, 1.0, 1.0, 1.0, 1.0, 1000000.0, -1000000.0]:
        result = normalizer.normalize(value)
        assert -1.0 < result < 1.0


def test_repeated_identical_values_converge_toward_zero_activation():
    normalizer = SensoryNormalizer()
    last = None
    for _ in range(50):
        last = normalizer.normalize(3.0)
    assert abs(last) < 0.05


def test_a_fresh_outlier_after_a_stable_baseline_produces_a_large_magnitude():
    normalizer = SensoryNormalizer()
    for _ in range(30):
        normalizer.normalize(1.0)
    outlier = normalizer.normalize(1000.0)
    assert abs(outlier) > 0.5


def test_z_score_clipping_bounds_extreme_outliers_consistently():
    normalizer = SensoryNormalizer()
    for _ in range(30):
        normalizer.normalize(1.0)
    huge = normalizer.normalize(1e9)
    normalizer2 = SensoryNormalizer()
    for _ in range(30):
        normalizer2.normalize(1.0)
    bigger = normalizer2.normalize(1e12)
    assert huge == pytest.approx(bigger, abs=1e-6)  # both clipped to the same z_max
```

```python
# tests/unit/cognition/test_types.py (append)
from symbiont.cognition.types import TAU_RANGE


def test_tau_range_matches_the_design_doc():
    assert TAU_RANGE == (0.1, 10.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_activation.py tests/unit/cognition/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.activation'`; `ImportError: cannot import name 'TAU_RANGE'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/types.py`:

```python
TAU_RANGE: tuple[float, float] = (0.1, 10.0)
```

```python
# src/symbiont/cognition/activation.py
from __future__ import annotations

import math
from dataclasses import dataclass

_EWMA_ALPHA = 0.06  # matches core/selfmodel.py's SELF_MODEL_EWMA_ALPHA convention
_VARIANCE_FLOOR = 1e-6


@dataclass(slots=True)
class SensoryNormalizer:
    """Converts a raw sensor reading into a bounded, graph-ready
    activation via a robust z-score against this sense's own running
    statistics, then a tanh squash (master doc §5.4). Independent per
    sense_id -- callers keep one instance per sense."""

    mean: float = 0.0
    variance: float = 0.0
    count: int = 0

    def normalize(self, raw_value: float, *, z_max: float = 4.0, softness: float = 2.0) -> float:
        stdev = math.sqrt(max(self.variance, _VARIANCE_FLOOR))
        z_score = (raw_value - self.mean) / stdev
        clipped = max(-z_max, min(z_max, z_score))
        activation = math.tanh(clipped / softness)

        self.count += 1
        if self.count == 1:
            self.mean = raw_value
            self.variance = 0.0
        else:
            delta = raw_value - self.mean
            self.mean += _EWMA_ALPHA * delta
            self.variance = (1.0 - _EWMA_ALPHA) * self.variance + _EWMA_ALPHA * delta * delta

        return activation
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_activation.py tests/unit/cognition/test_types.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/types.py src/symbiont/cognition/activation.py tests/unit/cognition/test_activation.py tests/unit/cognition/test_types.py
git commit -m "$(cat <<'EOF'
feat(cognition): add sensory normalization for graph inputs

SensoryNormalizer converts a raw reading into a bounded [-1, 1]
graph-ready activation via a robust z-score against its own running
mean/variance (same EWMA convention as core/selfmodel.py, alpha=0.06)
followed by a tanh squash, clipped at z_max before the squash so
arbitrarily large outliers never blow up the output. Also adds
TAU_RANGE (0.1, 10.0) to the closed range catalog for node
temperature validation.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 2: Graph data structures and construction validation (`cognition/graph.py`)

**Files:**
- Create: `src/symbiont/cognition/graph.py`
- Test: `tests/unit/cognition/test_graph.py`

**Interfaces:**
- Consumes: `NodeKind`, `EdgeKind`, `WEIGHT_RANGE`, `PLASTICITY_RANGE`, `EDGE_DELAY_TICKS_RANGE`, `TAU_RANGE` (Task 1 / v0.55 `types.py`); `KernelLimits` (v0.55 `limits.py`).
- Produces: `GraphError(ValueError)`, `PlasticNode`, `PlasticEdge`, `TickContext`, `GraphFrame`, `CognitiveGraph.__init__(*, nodes, edges, kernel_limits)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/cognition/test_graph.py
from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind


def _sense_node(node_id: str = "sense-a") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.SENSE)


def _concept_node(node_id: str = "concept-a", bias: float = 0.0, tau: float = 1.0) -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT, bias=bias, tau=tau)


def _edge(
    source: str = "sense-a",
    target: str = "concept-a",
    kind: EdgeKind = EdgeKind.EXCITATORY,
    weight: float = 1.0,
    delay_ticks: int = 0,
) -> PlasticEdge:
    return PlasticEdge(
        source_id=source, target_id=target, kind=kind, weight=weight, plasticity=0.5, delay_ticks=delay_ticks
    )


def test_valid_graph_constructs_without_error():
    CognitiveGraph(nodes=(_sense_node(), _concept_node()), edges=(_edge(),), kernel_limits=KernelLimits())


def test_rejects_duplicate_node_id():
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(_sense_node("x"), _concept_node("x")), edges=(), kernel_limits=KernelLimits())


def test_rejects_dangling_edge_source():
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_concept_node(),),
            edges=(_edge(source="ghost", target="concept-a"),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_dangling_edge_target():
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_sense_node(),),
            edges=(_edge(source="sense-a", target="ghost"),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_node_count_exceeding_kernel_limit():
    nodes = tuple(_concept_node(f"c{i}") for i in range(3))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits(max_nodes=2))


def test_rejects_edge_count_exceeding_kernel_limit():
    nodes = (_sense_node(), _concept_node("c1"), _concept_node("c2"))
    edges = (_edge(target="c1"), _edge(target="c2"))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits(max_edges=1))


def test_rejects_concept_count_exceeding_kernel_limit():
    nodes = tuple(_concept_node(f"c{i}") for i in range(3))
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits(max_concepts=2))


@pytest.mark.parametrize("tau", [0.05, 10.5])
def test_rejects_tau_outside_range(tau):
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=(_concept_node(tau=tau),), edges=(), kernel_limits=KernelLimits())


@pytest.mark.parametrize("weight", [-2.5, 2.5])
def test_rejects_weight_outside_range(weight):
    with pytest.raises(GraphError):
        CognitiveGraph(
            nodes=(_sense_node(), _concept_node()),
            edges=(_edge(weight=weight),),
            kernel_limits=KernelLimits(),
        )


def test_rejects_plasticity_outside_range():
    nodes = (_sense_node(), _concept_node())
    bad_edge = PlasticEdge(
        source_id="sense-a", target_id="concept-a", kind=EdgeKind.EXCITATORY, weight=1.0, plasticity=1.5, delay_ticks=0
    )
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_delay_outside_zero_or_one():
    nodes = (_sense_node(), _concept_node())
    bad_edge = PlasticEdge(
        source_id="sense-a", target_id="concept-a", kind=EdgeKind.EXCITATORY, weight=1.0, plasticity=0.5, delay_ticks=2
    )
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_delay_zero_from_a_non_sense_source():
    nodes = (_concept_node("a"), _concept_node("b"))
    bad_edge = _edge(source="a", target="b", delay_ticks=0)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_accepts_delay_one_from_a_non_sense_source():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())


def test_rejects_a_sense_node_with_an_incoming_edge():
    nodes = (_concept_node("a"), _sense_node("s"))
    bad_edge = _edge(source="a", target="s", delay_ticks=1)
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=(bad_edge,), kernel_limits=KernelLimits())


def test_rejects_duplicate_source_target_kind_edge():
    nodes = (_sense_node(), _concept_node())
    edges = (_edge(), _edge())
    with pytest.raises(GraphError):
        CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())


def test_allows_two_edges_same_endpoints_different_kind():
    nodes = (_sense_node(), _concept_node())
    edges = (_edge(kind=EdgeKind.EXCITATORY), _edge(kind=EdgeKind.GATING))
    CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_graph.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.cognition.graph'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/symbiont/cognition/graph.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .limits import KernelLimits
from .types import EDGE_DELAY_TICKS_RANGE, PLASTICITY_RANGE, TAU_RANGE, WEIGHT_RANGE, EdgeKind, NodeKind


class GraphError(ValueError):
    """Raised for an invalid graph topology or out-of-range node/edge
    field -- never a bare ValueError/KeyError/TypeError leaking internal
    structure, matching GenomeError's precedent."""


@dataclass(slots=True, frozen=True)
class PlasticNode:
    node_id: str
    kind: NodeKind
    bias: float = 0.0
    tau: float = 1.0


@dataclass(slots=True)
class PlasticEdge:
    source_id: str
    target_id: str
    kind: EdgeKind
    weight: float
    plasticity: float
    delay_ticks: int
    eligibility: float = 0.0
    support: int = 0
    age_ticks: int = 0
    stable_ticks: int = 0
    last_use_tick: int = 0


@dataclass(slots=True, frozen=True)
class TickContext:
    tick: int


@dataclass(slots=True, frozen=True)
class GraphFrame:
    tick: int
    activations: Mapping[str, float]
    readouts: Mapping[str, float]


def _require_range(value: float, bounds: tuple[float, float], field: str) -> None:
    low, high = bounds
    if not (low <= value <= high):
        raise GraphError(f"{field} ({value}) must be within [{low}, {high}]")


class CognitiveGraph:
    def __init__(self, *, nodes: tuple[PlasticNode, ...], edges: tuple[PlasticEdge, ...], kernel_limits: KernelLimits) -> None:
        self._nodes_by_id: dict[str, PlasticNode] = {}
        for node in nodes:
            if node.node_id in self._nodes_by_id:
                raise GraphError(f"duplicate node id {node.node_id!r}")
            _require_range(node.tau, TAU_RANGE, f"node {node.node_id!r} tau")
            self._nodes_by_id[node.node_id] = node

        if len(self._nodes_by_id) > kernel_limits.max_nodes:
            raise GraphError(f"node count ({len(self._nodes_by_id)}) exceeds kernel_limits.max_nodes ({kernel_limits.max_nodes})")

        concept_count = sum(1 for node in self._nodes_by_id.values() if node.kind is NodeKind.CONCEPT)
        if concept_count > kernel_limits.max_concepts:
            raise GraphError(f"concept count ({concept_count}) exceeds kernel_limits.max_concepts ({kernel_limits.max_concepts})")

        if len(edges) > kernel_limits.max_edges:
            raise GraphError(f"edge count ({len(edges)}) exceeds kernel_limits.max_edges ({kernel_limits.max_edges})")

        seen_edge_keys: set[tuple[str, str, EdgeKind]] = set()
        incoming_by_target: dict[str, list[PlasticEdge]] = {node_id: [] for node_id in self._nodes_by_id}
        for edge in edges:
            if edge.source_id not in self._nodes_by_id:
                raise GraphError(f"edge source {edge.source_id!r} is not a declared node")
            if edge.target_id not in self._nodes_by_id:
                raise GraphError(f"edge target {edge.target_id!r} is not a declared node")

            key = (edge.source_id, edge.target_id, edge.kind)
            if key in seen_edge_keys:
                raise GraphError(f"duplicate edge {key}")
            seen_edge_keys.add(key)

            _require_range(edge.weight, WEIGHT_RANGE, f"edge {edge.source_id}->{edge.target_id} weight")
            _require_range(edge.plasticity, PLASTICITY_RANGE, f"edge {edge.source_id}->{edge.target_id} plasticity")
            if edge.delay_ticks not in (EDGE_DELAY_TICKS_RANGE[0], EDGE_DELAY_TICKS_RANGE[1]):
                raise GraphError(f"edge {edge.source_id}->{edge.target_id} delay_ticks must be 0 or 1")

            source_kind = self._nodes_by_id[edge.source_id].kind
            if edge.delay_ticks == 0 and source_kind is not NodeKind.SENSE:
                raise GraphError(
                    f"edge {edge.source_id}->{edge.target_id} has delay_ticks=0 but source kind is "
                    f"{source_kind}, not SENSE -- only a SENSE source has a value available this tick"
                )

            target_kind = self._nodes_by_id[edge.target_id].kind
            if target_kind is NodeKind.SENSE:
                raise GraphError(f"SENSE node {edge.target_id!r} cannot have an incoming edge")

            incoming_by_target[edge.target_id].append(edge)

        self._edges = tuple(edges)
        self._incoming_by_target = incoming_by_target
        self._kernel_limits = kernel_limits

    @property
    def nodes(self) -> tuple[PlasticNode, ...]:
        return tuple(self._nodes_by_id.values())

    @property
    def edges(self) -> tuple[PlasticEdge, ...]:
        return self._edges
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_graph.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/graph.py tests/unit/cognition/test_graph.py
git commit -m "$(cat <<'EOF'
feat(cognition): add graph data structures and construction validation

PlasticNode (frozen), PlasticEdge (mutable, matching the master doc
exactly), TickContext, GraphFrame, and CognitiveGraph's full
construction-time validation: unique node ids, no dangling edges,
node/edge/concept counts within KernelLimits, weight/plasticity/tau/
delay ranges, delay_ticks=0 restricted to SENSE-kind sources (the only
node kind with a value available before graph propagation runs this
tick), no incoming edge on a SENSE node, and no duplicate
(source, target, kind) edges. No activation logic yet.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 3: Activation — contribution formula, delay, determinism, finiteness

**Files:**
- Modify: `src/symbiont/cognition/graph.py`
- Test: `tests/unit/cognition/test_graph.py`

**Interfaces:**
- Consumes: everything from Task 2.
- Produces: `CognitiveGraph.activate(self, inputs: Mapping[str, float], context: TickContext, *, previous: Mapping[str, float] | None = None) -> GraphFrame`. This task implements only non-`GATING` edges (`gate` term fixed at `1.0`); Task 4 adds gating.

- [ ] **Step 1: Write the failing tests**

```python
def test_activate_echoes_sense_inputs_directly():
    graph = CognitiveGraph(nodes=(_sense_node(),), edges=(), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 0.7}, context=TickContext(tick=1))
    assert frame.activations["sense-a"] == 0.7


def test_activate_computes_bias_only_with_no_edges():
    import math

    graph = CognitiveGraph(nodes=(_concept_node(bias=0.5, tau=1.0),), edges=(), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={}, context=TickContext(tick=1))
    assert frame.activations["concept-a"] == pytest.approx(math.tanh(0.5))


def test_delay_zero_sense_edge_reacts_immediately():
    graph = CognitiveGraph(nodes=(_sense_node(), _concept_node()), edges=(_edge(delay_ticks=0),), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 1.0}, context=TickContext(tick=1))
    assert frame.activations["concept-a"] > 0.5


def test_delay_one_edge_ignores_this_ticks_input_uses_previous():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    graph = CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={}, context=TickContext(tick=2), previous={"a": 1.0, "b": 0.0})
    assert frame.activations["b"] > 0.5  # picked up "a"'s previous-tick value


def test_cold_start_with_no_previous_treats_delay_one_sources_as_zero():
    nodes = (_concept_node("a"), _concept_node("b"))
    edge = _edge(source="a", target="b", delay_ticks=1)
    graph = CognitiveGraph(nodes=nodes, edges=(edge,), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={}, context=TickContext(tick=1), previous=None)
    assert frame.activations["b"] == pytest.approx(0.0)


def test_activation_is_independent_of_node_and_edge_construction_order():
    nodes_forward = (_sense_node(), _concept_node("c1"), _concept_node("c2"))
    edges_forward = (_edge(target="c1"), _edge(target="c2"))
    graph_forward = CognitiveGraph(nodes=nodes_forward, edges=edges_forward, kernel_limits=KernelLimits())

    nodes_reversed = tuple(reversed(nodes_forward))
    edges_reversed = tuple(reversed(edges_forward))
    graph_reversed = CognitiveGraph(nodes=nodes_reversed, edges=edges_reversed, kernel_limits=KernelLimits())

    frame_forward = graph_forward.activate(inputs={"sense-a": 0.6}, context=TickContext(tick=1))
    frame_reversed = graph_reversed.activate(inputs={"sense-a": 0.6}, context=TickContext(tick=1))
    assert dict(frame_forward.activations) == dict(frame_reversed.activations)


def test_extreme_inputs_never_produce_nan_or_inf():
    graph = CognitiveGraph(nodes=(_sense_node(), _concept_node(bias=1e6)), edges=(_edge(weight=2.0),), kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 1e12}, context=TickContext(tick=1))
    import math

    for value in frame.activations.values():
        assert math.isfinite(value)


def test_readouts_contains_only_readout_kind_nodes():
    nodes = (_sense_node(), _concept_node(), PlasticNode(node_id="r1", kind=NodeKind.READOUT, bias=0.1))
    edges = (_edge(target="concept-a"),)
    graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=KernelLimits())
    frame = graph.activate(inputs={"sense-a": 0.5}, context=TickContext(tick=1))
    assert set(frame.readouts.keys()) == {"r1"}
    assert "concept-a" not in frame.readouts
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_graph.py -v -k "activate or delay or independent_of or extreme_inputs or readouts_contains"`
Expected: FAIL — `AttributeError: 'CognitiveGraph' object has no attribute 'activate'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/symbiont/cognition/graph.py`:

```python
import math
```

(near the top, with the other imports)

```python
    def activate(
        self,
        inputs: Mapping[str, float],
        context: TickContext,
        *,
        previous: Mapping[str, float] | None = None,
    ) -> GraphFrame:
        previous_frame = previous if previous is not None else {}

        def source_value(edge: PlasticEdge) -> float:
            if edge.delay_ticks == 0:
                return inputs.get(edge.source_id, 0.0)
            return previous_frame.get(edge.source_id, 0.0)

        new_activations: dict[str, float] = {}
        for node_id, node in self._nodes_by_id.items():
            if node.kind is NodeKind.SENSE:
                new_activations[node_id] = float(inputs.get(node_id, 0.0))
                continue

            total = node.bias
            for edge in self._incoming_by_target[node_id]:
                if edge.kind is EdgeKind.GATING:
                    continue  # Task 4 adds gating; non-gating edges use gate=1.0 for now
                total += edge.weight * source_value(edge)

            activation = math.tanh(total / node.tau)
            if not math.isfinite(activation):
                raise GraphError(f"node {node_id!r} produced a non-finite activation")
            new_activations[node_id] = activation

        readouts = {
            node_id: value
            for node_id, value in new_activations.items()
            if self._nodes_by_id[node_id].kind is NodeKind.READOUT
        }
        return GraphFrame(tick=context.tick, activations=new_activations, readouts=readouts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_graph.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/graph.py tests/unit/cognition/test_graph.py
git commit -m "$(cat <<'EOF'
feat(cognition): add graph activation (contribution formula, no gating yet)

CognitiveGraph.activate() computes one synchronous double-buffered
pass: SENSE nodes echo this tick's inputs directly, every other node
sums bias plus delay-routed edge contributions (delay=0 reads this
tick's inputs, delay=1 reads last tick's frame) and squashes through
tanh(total / tau). Reads only from the two supplied frames, never
from values computed earlier in the same call, which is what makes
the result independent of node/edge construction order. Every
activation is finiteness-checked. GATING edges are parsed and
validated but contribute nothing yet -- gate stays fixed at 1.0 until
Task 4.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Task 4: Gating

**Files:**
- Modify: `src/symbiont/cognition/graph.py`
- Test: `tests/unit/cognition/test_graph.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces: no new public interface — `activate()`'s behavior for `GATING` edges changes from Task 3's placeholder.

- [ ] **Step 1: Write the failing tests**

```python
def test_gating_edge_near_zero_suppresses_a_co_targeting_edge():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gating = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gating), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={"gate-source": 0.0, "signal-source": 1.0}, context=TickContext(tick=1))
    assert abs(frame.activations["concept-a"]) < 0.05


def test_gating_edge_near_one_passes_signal_through():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gating = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gating), kernel_limits=KernelLimits())

    frame_open = graph.activate(inputs={"gate-source": 1.0, "signal-source": 1.0}, context=TickContext(tick=1))
    ungated_graph = CognitiveGraph(nodes=(_sense_node("signal-source"), _concept_node()), edges=(contributing,), kernel_limits=KernelLimits())
    frame_ungated = ungated_graph.activate(inputs={"signal-source": 1.0}, context=TickContext(tick=1))
    assert frame_open.activations["concept-a"] == pytest.approx(frame_ungated.activations["concept-a"], abs=1e-6)


def test_two_gating_edges_combine_by_product():
    nodes = (_sense_node("gate-a"), _sense_node("gate-b"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    gate_a = PlasticEdge(source_id="gate-a", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0)
    gate_b = PlasticEdge(source_id="gate-b", target_id="concept-a", kind=EdgeKind.GATING, weight=1.0, plasticity=0.5, delay_ticks=0)
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, gate_a, gate_b), kernel_limits=KernelLimits())

    frame_both_open = graph.activate(
        inputs={"gate-a": 1.0, "gate-b": 1.0, "signal-source": 1.0}, context=TickContext(tick=1)
    )
    frame_one_closed = graph.activate(
        inputs={"gate-a": 1.0, "gate-b": 0.0, "signal-source": 1.0}, context=TickContext(tick=1)
    )
    assert abs(frame_one_closed.activations["concept-a"]) < abs(frame_both_open.activations["concept-a"])


def test_gating_edge_weight_scales_before_clipping():
    nodes = (_sense_node("gate-source"), _sense_node("signal-source"), _concept_node())
    contributing = _edge(source="signal-source", target="concept-a", weight=2.0, delay_ticks=0)
    negative_gate = PlasticEdge(
        source_id="gate-source", target_id="concept-a", kind=EdgeKind.GATING, weight=-1.0, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=nodes, edges=(contributing, negative_gate), kernel_limits=KernelLimits())

    frame = graph.activate(inputs={"gate-source": 1.0, "signal-source": 1.0}, context=TickContext(tick=1))
    # weight * activation = -1.0, clipped to [0, 1] -> gate fully closed
    assert abs(frame.activations["concept-a"]) < 0.05
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cognition/test_graph.py -v -k gating`
Expected: FAIL — the "near one passes signal through" and "combine by product" assertions fail because Task 3's `activate()` ignores `GATING` edges entirely (equivalent to always-open, so the "near zero suppresses" test likely already spuriously passes only because gating is skipped and the *raw* signal still produces a non-trivial activation — verify each assertion actually exercises the gate rather than coincidentally passing before concluding a real failure; the "combine by product" and "weight scales" tests cannot pass without real gating logic).

- [ ] **Step 3: Write minimal implementation**

Replace the `activate()` body's per-node loop in `src/symbiont/cognition/graph.py`:

```python
        new_activations: dict[str, float] = {}
        for node_id, node in self._nodes_by_id.items():
            if node.kind is NodeKind.SENSE:
                new_activations[node_id] = float(inputs.get(node_id, 0.0))
                continue

            incoming = self._incoming_by_target[node_id]
            gate = 1.0
            for edge in incoming:
                if edge.kind is not EdgeKind.GATING:
                    continue
                component = edge.weight * source_value(edge)
                component = max(0.0, min(1.0, component))
                gate *= component

            total = node.bias
            for edge in incoming:
                if edge.kind is EdgeKind.GATING:
                    continue
                total += gate * edge.weight * source_value(edge)

            activation = math.tanh(total / node.tau)
            if not math.isfinite(activation):
                raise GraphError(f"node {node_id!r} produced a non-finite activation")
            new_activations[node_id] = activation
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cognition/test_graph.py -v`
Expected: PASS, all tests including every test from Tasks 2-3.

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/cognition/graph.py tests/unit/cognition/test_graph.py
git commit -m "$(cat <<'EOF'
feat(cognition): add GATING edge modulation to graph activation

A GATING edge's source activation, scaled by the edge's own weight
and clipped to [0, 1], multiplies every other (non-GATING) edge
sharing its target. Multiple GATING edges targeting the same node
combine by product -- any one closed gate suppresses the target,
the conservative choice given the master design doc specifies no
combination rule. Closes out v0.56's standalone activation engine.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K8MsjKLjXKm4dR8k5xo4iE
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:**
- §4.2 sensory normalization → Task 1.
- §4.3 data structures, `TAU_RANGE` → Tasks 1, 2.
- §4.4 construction validation (all bullets) → Task 2.
- §4.4 `activate()` steps 1-4 (contribution formula, delay routing, SENSE echo) → Task 3.
- §3.1 gating resolution → Task 4.
- §3.2 delay resolution (validation) → Task 2; (routing in `activate()`) → Task 3.
- §4.4 step 5 (finiteness) → Task 3.
- Non-goals (§2): no task adds learning, eligibility updates, structural mutation, genome-to-topology generation, or runtime tick-loop wiring.

**Type consistency check:** `PlasticEdge.delay_ticks` (Task 2) is read identically by `source_value()` in Tasks 3 and 4. `GraphFrame.readouts`/`.activations` field names match every test's usage across Tasks 3-4. `CognitiveGraph.activate()`'s signature (`inputs`, `context`, `previous`) is introduced once in Task 3 and never changes shape in Task 4 — only the gating logic inside its body changes.
