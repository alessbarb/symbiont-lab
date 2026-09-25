from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Mapping

from .limits import KernelLimits
from .types import (
    EDGE_DELAY_TICKS_RANGE,
    PLASTICITY_RANGE,
    TAU_RANGE,
    WEIGHT_RANGE,
    EdgeKind,
    NodeKind,
)

_NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


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
    predicts_node_id: str | None = None


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
    if not math.isfinite(value):
        raise GraphError(f"{field} must be finite")
    if not (low <= value <= high):
        raise GraphError(f"{field} ({value}) must be within [{low}, {high}]")


class CognitiveGraph:
    def __init__(
        self,
        *,
        nodes: tuple[PlasticNode, ...],
        edges: tuple[PlasticEdge, ...],
        kernel_limits: KernelLimits,
    ) -> None:
        self._nodes_by_id: dict[str, PlasticNode] = {}
        for node in nodes:
            if not _NODE_ID_PATTERN.match(node.node_id):
                raise GraphError(f"node_id {node.node_id!r} must match ^[A-Za-z0-9_.-]{{1,128}}$")
            if node.node_id in self._nodes_by_id:
                raise GraphError(f"duplicate node id {node.node_id!r}")
            if not math.isfinite(node.bias):
                raise GraphError(f"node {node.node_id!r} bias must be finite")
            _require_range(node.tau, TAU_RANGE, f"node {node.node_id!r} tau")
            self._nodes_by_id[node.node_id] = node

        for node in self._nodes_by_id.values():
            if node.kind is NodeKind.PREDICTOR:
                if node.predicts_node_id is None:
                    raise GraphError(f"PREDICTOR node {node.node_id!r} must set predicts_node_id")
                if not _NODE_ID_PATTERN.match(node.predicts_node_id):
                    raise GraphError(
                        f"predicts_node_id {node.predicts_node_id!r} must match ^[A-Za-z0-9_.-]{{1,128}}$"
                    )
                if node.predicts_node_id not in self._nodes_by_id:
                    raise GraphError(
                        f"PREDICTOR node {node.node_id!r} predicts_node_id "
                        f"{node.predicts_node_id!r} is not a declared node"
                    )
            elif node.predicts_node_id is not None:
                raise GraphError(
                    f"non-PREDICTOR node {node.node_id!r} must not set predicts_node_id"
                )

        if len(self._nodes_by_id) > kernel_limits.max_nodes:
            raise GraphError(
                f"node count ({len(self._nodes_by_id)}) exceeds kernel_limits.max_nodes ({kernel_limits.max_nodes})"
            )

        concept_count = sum(
            1 for node in self._nodes_by_id.values() if node.kind is NodeKind.CONCEPT
        )
        if concept_count > kernel_limits.max_concepts:
            raise GraphError(
                f"concept count ({concept_count}) exceeds kernel_limits.max_concepts ({kernel_limits.max_concepts})"
            )

        if len(edges) > kernel_limits.max_edges:
            raise GraphError(
                f"edge count ({len(edges)}) exceeds kernel_limits.max_edges ({kernel_limits.max_edges})"
            )

        seen_edge_keys: set[tuple[str, str, EdgeKind]] = set()
        incoming_by_target: dict[str, list[PlasticEdge]] = {
            node_id: [] for node_id in self._nodes_by_id
        }
        incident_by_node: dict[str, list[PlasticEdge]] = {
            node_id: [] for node_id in self._nodes_by_id
        }
        for edge in edges:
            if edge.source_id not in self._nodes_by_id:
                raise GraphError(f"edge source {edge.source_id!r} is not a declared node")
            if edge.target_id not in self._nodes_by_id:
                raise GraphError(f"edge target {edge.target_id!r} is not a declared node")

            key = (edge.source_id, edge.target_id, edge.kind)
            if key in seen_edge_keys:
                raise GraphError(f"duplicate edge {key}")
            seen_edge_keys.add(key)

            _require_range(
                edge.weight, WEIGHT_RANGE, f"edge {edge.source_id}->{edge.target_id} weight"
            )
            _require_range(
                edge.plasticity,
                PLASTICITY_RANGE,
                f"edge {edge.source_id}->{edge.target_id} plasticity",
            )
            if edge.delay_ticks not in (EDGE_DELAY_TICKS_RANGE[0], EDGE_DELAY_TICKS_RANGE[1]):
                raise GraphError(
                    f"edge {edge.source_id}->{edge.target_id} delay_ticks must be 0 or 1"
                )

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
            # Matches `[e for e in edges if e.source_id == n or e.target_id == n]`
            # exactly: a self-loop edge (source_id == target_id) is included
            # once, not twice.
            incident_by_node[edge.source_id].append(edge)
            if edge.target_id != edge.source_id:
                incident_by_node[edge.target_id].append(edge)

        self._edges = tuple(edges)
        # CognitiveGraph is immutable after construction: structural changes
        # create a new graph. Keep the stable node view instead of rebuilding
        # it on every property access during a cognitive tick.
        self._nodes = tuple(self._nodes_by_id.values())
        self._incoming_by_target = incoming_by_target
        self._incident_by_node = {
            node_id: tuple(node_edges) for node_id, node_edges in incident_by_node.items()
        }
        self._kernel_limits = kernel_limits

    def node_by_id(self, node_id: str) -> PlasticNode | None:
        """O(1) node lookup — prefer this over scanning `.nodes` linearly."""
        return self._nodes_by_id.get(node_id)

    def incident_edges(self, node_id: str) -> tuple[PlasticEdge, ...]:
        """O(1) lookup of every edge touching ``node_id`` (source or target).

        Equivalent to
        ``tuple(e for e in self.edges if e.source_id == node_id or e.target_id == node_id)``
        but precomputed once at construction (the graph never mutates after
        __init__ — a "mutation" builds a whole new CognitiveGraph), so this
        index can never go stale.
        """
        return self._incident_by_node.get(node_id, ())

    @property
    def nodes(self) -> tuple[PlasticNode, ...]:
        return self._nodes

    @property
    def edges(self) -> tuple[PlasticEdge, ...]:
        return self._edges

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

        readouts = {
            node_id: value
            for node_id, value in new_activations.items()
            if self._nodes_by_id[node_id].kind is NodeKind.READOUT
        }
        return GraphFrame(tick=context.tick, activations=new_activations, readouts=readouts)


def load_graph_definition(
    payload: Mapping[str, object], *, kernel_limits: KernelLimits
) -> CognitiveGraph:
    """Constructs a graph from an explicit, owner-authored JSON-shaped
    definition -- raw floats throughout, not quantized. Unlike
    cognition.checkpoint's export/restore (which persists continuously-
    updated learned state and must guard against differencing attacks),
    this is a one-time initial declaration the owner wrote themselves;
    there is no "recent activation" to leak by exporting it exactly.
    Construction validation (ranges, delay/sense rules, kernel limits)
    is reused as-is from CognitiveGraph.__init__ -- this function does
    no additional validation of its own."""
    nodes = tuple(
        PlasticNode(
            node_id=str(entry["node_id"]),
            kind=NodeKind(entry["kind"]),
            bias=float(entry.get("bias", 0.0)),
            tau=float(entry.get("tau", 1.0)),
            predicts_node_id=entry.get("predicts_node_id"),
        )
        for entry in payload["nodes"]
    )
    edges = tuple(
        PlasticEdge(
            source_id=str(entry["source_id"]),
            target_id=str(entry["target_id"]),
            kind=EdgeKind(entry["kind"]),
            weight=float(entry["weight"]),
            plasticity=float(entry.get("plasticity", 0.5)),
            delay_ticks=int(entry.get("delay_ticks", 1)),
        )
        for entry in payload["edges"]
    )
    return CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=kernel_limits)
