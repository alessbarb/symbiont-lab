from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Collection, Literal, Mapping

from .graph import CognitiveGraph, PlasticEdge, PlasticNode
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

    def reconcile(self, allowed_node_ids: Collection[str]) -> None:
        """Drop tracked state referencing nodes that no longer exist."""
        allowed = set(allowed_node_ids)
        self._coactivation_counts = {
            pair: count
            for pair, count in self._coactivation_counts.items()
            if pair[0] in allowed and pair[1] in allowed
        }
        self._cooldown_until = {
            node_id: until for node_id, until in self._cooldown_until.items() if node_id in allowed
        }

    def observe_coactivation(
        self, *, source_id: str, target_id: str, source_active: bool, target_active: bool, tick: int
    ) -> None:
        if source_active and target_active:
            key = (source_id, target_id)
            self._coactivation_counts[key] = self._coactivation_counts.get(key, 0) + 1

    def export_checkpoint(self) -> dict[str, object]:
        """Persist only bounded structural evidence, never activations.

        Coactivation support and cooldown deadlines are organism-relative
        integer metadata. They preserve learning progress across a resident
        restart without retaining the values that caused the coactivation.
        """
        return {
            "coactivation_counts": [
                {"source_id": source_id, "target_id": target_id, "count": count}
                for (source_id, target_id), count in sorted(self._coactivation_counts.items())
                if count > 0
            ],
            "cooldown_until": dict(sorted(self._cooldown_until.items())),
        }

    @classmethod
    def restore_checkpoint(
        cls,
        payload: Mapping[str, object] | None,
        *,
        min_candidate_support: int,
        tentative_lifetime_ticks: int,
        cooldown_ticks: int,
        allowed_node_ids: Collection[str],
    ) -> "StructuralPlasticity":
        """Restore bounded structural evidence against the current graph.

        The graph is authoritative: checkpoint entries for removed or unknown
        node ids are ignored. Input size is capped by the maximum number of
        ordered pairs the current graph can actually represent.
        """
        model = cls(
            min_candidate_support=min_candidate_support,
            tentative_lifetime_ticks=tentative_lifetime_ticks,
            cooldown_ticks=cooldown_ticks,
        )
        if not payload:
            return model
        if not isinstance(payload, Mapping):
            raise ValueError("structural plasticity checkpoint must be an object")

        allowed = set(allowed_node_ids)
        raw_counts = payload.get("coactivation_counts", [])
        if not isinstance(raw_counts, list):
            raise ValueError("coactivation_counts must be a list")
        max_pairs = len(allowed) * max(0, len(allowed) - 1)
        for entry in raw_counts[:max_pairs]:
            if not isinstance(entry, Mapping):
                raise ValueError("coactivation count entry must be an object")
            source_id = str(entry["source_id"])
            target_id = str(entry["target_id"])
            raw_count: Any = entry["count"]
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
                raise ValueError("coactivation count must be a positive integer")
            if source_id in allowed and target_id in allowed and source_id != target_id:
                model._coactivation_counts[(source_id, target_id)] = raw_count

        raw_cooldowns = payload.get("cooldown_until", {})
        if not isinstance(raw_cooldowns, Mapping):
            raise ValueError("cooldown_until must be an object")
        for node_id, raw_until in raw_cooldowns.items():
            if isinstance(raw_until, bool) or not isinstance(raw_until, int) or raw_until < 0:
                raise ValueError("cooldown tick must be a non-negative integer")
            node_id = str(node_id)
            if node_id in allowed:
                model._cooldown_until[node_id] = raw_until

        return model

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


def _edge_key(payload: Mapping[str, object]) -> tuple[str, str, object]:
    return (payload["source_id"], payload["target_id"], payload["kind"])


def validate_mutation(mutation: Mutation, graph: CognitiveGraph, kernel_limits: KernelLimits) -> ValidationResult:
    node_ids = {node.node_id for node in graph.nodes}

    if mutation.kind == "add_edge":
        source_id = mutation.payload["source_id"]
        target_id = mutation.payload["target_id"]
        if source_id not in node_ids:
            return ValidationResult(accepted=False, reason=f"source {source_id!r} is not a declared node")
        if target_id not in node_ids:
            return ValidationResult(accepted=False, reason=f"target {target_id!r} is not a declared node")
        if len(graph.edges) >= kernel_limits.max_edges:
            return ValidationResult(accepted=False, reason="kernel edge budget exhausted")
        return ValidationResult(accepted=True)

    if mutation.kind == "add_node":
        node_id = mutation.payload["node_id"]
        if node_id in node_ids:
            return ValidationResult(accepted=False, reason=f"node id {node_id!r} already exists")
        if len(graph.nodes) >= kernel_limits.max_nodes:
            return ValidationResult(accepted=False, reason="kernel node budget exhausted")
        if mutation.payload.get("kind") is NodeKind.CONCEPT:
            concept_count = sum(1 for node in graph.nodes if node.kind is NodeKind.CONCEPT)
            if concept_count >= kernel_limits.max_concepts:
                return ValidationResult(accepted=False, reason="kernel concept budget exhausted")
        source_ids = mutation.payload.get("source_ids", ())
        missing = [source_id for source_id in source_ids if source_id not in node_ids]
        if missing:
            return ValidationResult(accepted=False, reason=f"source ids not declared: {missing}")
        if len(graph.edges) + len(source_ids) > kernel_limits.max_edges:
            return ValidationResult(accepted=False, reason="kernel edge budget exhausted for concept wiring")
        return ValidationResult(accepted=True)

    if mutation.kind in ("remove_edge", "quarantine_edge"):
        key = _edge_key(mutation.payload)
        existing_keys = {(edge.source_id, edge.target_id, edge.kind) for edge in graph.edges}
        if key not in existing_keys:
            return ValidationResult(accepted=False, reason=f"no such edge {key}")
        return ValidationResult(accepted=True)

    return ValidationResult(accepted=False, reason=f"unsupported mutation kind {mutation.kind!r} in this version")


def apply_mutations(
    graph: CognitiveGraph, mutations: tuple[Mutation, ...], kernel_limits: KernelLimits, *, frozen: bool = False
) -> CognitiveGraph:
    if frozen:
        return graph

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
        elif mutation.kind == "add_node":
            nodes.append(PlasticNode(node_id=mutation.payload["node_id"], kind=mutation.payload["kind"]))
            for source_id in mutation.payload.get("source_ids", ()):
                edges.append(
                    PlasticEdge(
                        source_id=source_id,
                        target_id=mutation.payload["node_id"],
                        kind=EdgeKind.EXCITATORY,
                        weight=_TENTATIVE_INITIAL_WEIGHT,
                        plasticity=0.5,
                        delay_ticks=1,
                    )
                )
        elif mutation.kind == "remove_edge":
            key = _edge_key(mutation.payload)
            edges = [edge for edge in edges if (edge.source_id, edge.target_id, edge.kind) != key]
        elif mutation.kind == "quarantine_edge":
            pass

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
    tentative_lifetime_ticks: int = 0,
) -> EdgeLifecycleState:
    if edge.support < minimum_support:
        if tentative_lifetime_ticks > 0 and edge.age_ticks >= tentative_lifetime_ticks:
            return EdgeLifecycleState.REMOVED
        return EdgeLifecycleState.ACTIVE
    if abs(edge.weight) >= prune_threshold:
        return EdgeLifecycleState.ACTIVE

    stale_ticks = current_tick - edge.last_use_tick
    if stale_ticks < quarantine_window_ticks:
        return EdgeLifecycleState.WEAK
    if stale_ticks < 2 * quarantine_window_ticks:
        return EdgeLifecycleState.QUARANTINED
    return EdgeLifecycleState.REMOVED


def advance_edge_age(edge: PlasticEdge, *, tick: int, used: bool) -> None:
    """Age an edge and record real use support."""
    edge.age_ticks += 1
    if used:
        edge.support += 1
        edge.last_use_tick = tick
