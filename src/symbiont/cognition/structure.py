from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Mapping

from .graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from .limits import KernelLimits
from .types import EdgeKind, NodeKind

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
        candidate_graph = CognitiveGraph(nodes=tuple(nodes), edges=tuple(edges), kernel_limits=kernel_limits)
        result = validate_mutation(mutation, candidate_graph, kernel_limits)
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
        return EdgeLifecycleState.ACTIVE
    if abs(edge.weight) >= prune_threshold:
        return EdgeLifecycleState.ACTIVE

    stale_ticks = current_tick - edge.last_use_tick
    if stale_ticks < quarantine_window_ticks:
        return EdgeLifecycleState.WEAK
    if stale_ticks < 2 * quarantine_window_ticks:
        return EdgeLifecycleState.QUARANTINED
    return EdgeLifecycleState.REMOVED
