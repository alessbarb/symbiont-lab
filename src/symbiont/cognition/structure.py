from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Collection, Literal, Mapping

from .graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from .limits import KernelLimits
from .types import EdgeKind, NodeKind

_TENTATIVE_INITIAL_WEIGHT = 0.05

MutationKind = Literal["add_edge", "add_node", "quarantine_edge", "remove_edge", "remove_node"]


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
        self._motor_association_counts: dict[tuple[str, str], int] = {}
        self._cooldown_until: dict[str, int] = {}

    def reconcile(self, allowed_node_ids: Collection[str]) -> None:
        """Drop tracked state referencing nodes that no longer exist."""
        allowed = set(allowed_node_ids)
        self._coactivation_counts = {
            pair: count
            for pair, count in self._coactivation_counts.items()
            if pair[0] in allowed and pair[1] in allowed
        }
        self._motor_association_counts = {
            pair: count
            for pair, count in self._motor_association_counts.items()
            if pair[0] in allowed and pair[1] in allowed
        }
        self._cooldown_until = {
            node_id: until for node_id, until in self._cooldown_until.items() if node_id in allowed
        }

    def observe_coactivation(
        self,
        *,
        source_id: str,
        target_id: str,
        source_active: bool,
        target_active: bool,
        tick: int,
        source_kind: NodeKind | None = None,
        target_kind: NodeKind | None = None,
    ) -> None:
        """Accumulate evidence only for structurally legal generic edges.

        A SENSE may be a source but can never be a target in CognitiveGraph.
        SENSE↔SENSE coactivity therefore belongs to the separate concept
        candidate mechanism and must not consume generic edge-candidate
        memory. ``source_kind``/``target_kind`` are optional for backwards
        compatibility with direct unit/lab callers that already provide a
        prevalidated pair; the resident bridge always supplies both kinds.
        """
        del tick  # retained in the public signature for future time-aware evidence
        if target_kind is NodeKind.SENSE:
            return
        if source_kind is NodeKind.SENSE and target_kind is NodeKind.SENSE:
            return
        if source_active and target_active:
            key = (source_id, target_id)
            self._coactivation_counts[key] = self._coactivation_counts.get(key, 0) + 1

    def mark_relation_explained(self, source_id: str, target_id: str) -> None:
        """Consume stale growth evidence once structure already explains a pair.

        If the relation later disappears, new growth must earn fresh evidence
        instead of resurrecting immediately from historical support.
        """
        self._coactivation_counts.pop((source_id, target_id), None)
        self._motor_association_counts.pop((source_id, target_id), None)

    def observe_motor_association_evidence(
        self,
        *,
        source_id: str,
        motor_readout_id: str,
        source_active: bool,
        actuator_has_effect_evidence: bool,
        tick: int,
    ) -> None:
        """Track motor association evidence without faking READOUT activity."""
        del tick
        if source_id == motor_readout_id:
            return
        if source_active and actuator_has_effect_evidence:
            key = (source_id, motor_readout_id)
            self._motor_association_counts[key] = self._motor_association_counts.get(key, 0) + 1

    def export_checkpoint(self) -> dict[str, object]:
        """Persist only bounded structural evidence, never activations."""
        return {
            "coactivation_counts": [
                {"source_id": source_id, "target_id": target_id, "count": count}
                for (source_id, target_id), count in sorted(self._coactivation_counts.items())
                if count > 0
            ],
            "motor_association_counts": [
                {"source_id": source_id, "target_id": target_id, "count": count}
                for (source_id, target_id), count in sorted(self._motor_association_counts.items())
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

        raw_motor_counts = payload.get("motor_association_counts", [])
        if not isinstance(raw_motor_counts, list):
            raise ValueError("motor_association_counts must be a list")
        for entry in raw_motor_counts[:max_pairs]:
            if not isinstance(entry, Mapping):
                raise ValueError("motor association count entry must be an object")
            source_id = str(entry["source_id"])
            target_id = str(entry["target_id"])
            raw_count: Any = entry["count"]
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
                raise ValueError("motor association count must be a positive integer")
            if source_id in allowed and target_id in allowed and source_id != target_id:
                model._motor_association_counts[(source_id, target_id)] = raw_count

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

    def propose(
        self,
        graph: CognitiveGraph,
        *,
        kernel_limits: KernelLimits,
        tick: int,
        max_mutations: int | None = None,
    ) -> tuple[Mutation, ...]:
        """Propose only mutations that can fit the hard kernel envelope.

        The caller may reserve part of the per-consolidation mutation budget
        for pruning through ``max_mutations``. Cooldowns are recorded only for
        proposals that are actually emitted, so a mutation dropped by a hard
        cap never suppresses a future legitimate proposal.
        """
        budget = kernel_limits.max_structural_mutations_per_consolidation
        if max_mutations is not None:
            budget = max(0, min(budget, max_mutations))
        if budget == 0:
            return ()

        existing_pairs = {(edge.source_id, edge.target_id) for edge in graph.edges}
        node_ids = {node.node_id for node in graph.nodes}
        tentative_count = sum(1 for edge in graph.edges if edge.support < self._min_candidate_support)
        mutations: list[Mutation] = []

        candidate_counts = dict(self._coactivation_counts)
        for pair, count in self._motor_association_counts.items():
            candidate_counts[pair] = max(candidate_counts.get(pair, 0), count)

        for (source_id, target_id), count in sorted(candidate_counts.items()):
            if len(mutations) >= budget:
                break
            if count < self._min_candidate_support:
                continue
            if source_id not in node_ids or target_id not in node_ids:
                continue
            if (source_id, target_id) in existing_pairs:
                continue
            if len(graph.edges) + len(mutations) >= kernel_limits.max_edges:
                continue
            if tentative_count + len(mutations) >= kernel_limits.max_tentative_edges:
                continue
            if self._cooldown_until.get(source_id, -1) >= tick or self._cooldown_until.get(target_id, -1) >= tick:
                continue

            mutation = Mutation(
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
            if not validate_mutation(mutation, graph, kernel_limits).accepted:
                continue
            mutations.append(mutation)
            self._cooldown_until[source_id] = tick + self._cooldown_ticks
            self._cooldown_until[target_id] = tick + self._cooldown_ticks

        return tuple(mutations)


@dataclass(slots=True, frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None = None


def _edge_key(payload: Mapping[str, object]) -> tuple[str, str, object]:
    return (str(payload["source_id"]), str(payload["target_id"]), EdgeKind(payload["kind"]))


def _edge_from_payload(payload: Mapping[str, object]) -> PlasticEdge:
    return PlasticEdge(
        source_id=str(payload["source_id"]),
        target_id=str(payload["target_id"]),
        kind=EdgeKind(payload["kind"]),
        weight=float(payload["weight"]),
        plasticity=float(payload["plasticity"]),
        delay_ticks=int(payload["delay_ticks"]),
    )


def _node_from_payload(payload: Mapping[str, object]) -> PlasticNode:
    return PlasticNode(
        node_id=str(payload["node_id"]),
        kind=NodeKind(payload["kind"]),
        bias=float(payload.get("bias", 0.0)),
        tau=float(payload.get("tau", 1.0)),
        predicts_node_id=payload.get("predicts_node_id"),
    )


def validate_mutation(mutation: Mutation, graph: CognitiveGraph, kernel_limits: KernelLimits) -> ValidationResult:
    """Validate a mutation against the same invariants as CognitiveGraph.

    Validation materializes a candidate graph instead of duplicating only a
    subset of graph rules. This prevents a mutation accepted here from later
    crashing graph reconstruction because, for example, it targets a SENSE
    node or carries an invalid delay/weight.
    """
    try:
        if mutation.kind == "add_edge":
            edge = _edge_from_payload(mutation.payload)
            CognitiveGraph(
                nodes=graph.nodes,
                edges=(*graph.edges, edge),
                kernel_limits=kernel_limits,
            )
            return ValidationResult(accepted=True)

        if mutation.kind == "add_node":
            node = _node_from_payload(mutation.payload)
            source_ids = tuple(str(source_id) for source_id in mutation.payload.get("source_ids", ()))
            new_edges = tuple(
                PlasticEdge(
                    source_id=source_id,
                    target_id=node.node_id,
                    kind=EdgeKind.EXCITATORY,
                    weight=_TENTATIVE_INITIAL_WEIGHT,
                    plasticity=0.5,
                    delay_ticks=1,
                )
                for source_id in source_ids
            )
            CognitiveGraph(
                nodes=(*graph.nodes, node),
                edges=(*graph.edges, *new_edges),
                kernel_limits=kernel_limits,
            )
            return ValidationResult(accepted=True)

        if mutation.kind in ("remove_edge", "quarantine_edge"):
            key = _edge_key(mutation.payload)
            existing_keys = {(edge.source_id, edge.target_id, edge.kind) for edge in graph.edges}
            if key not in existing_keys:
                return ValidationResult(accepted=False, reason=f"no such edge {key}")
            return ValidationResult(accepted=True)

        if mutation.kind == "remove_node":
            node_id = str(mutation.payload["node_id"])
            node_ids = {node.node_id for node in graph.nodes}
            if node_id not in node_ids:
                return ValidationResult(accepted=False, reason=f"no such node {node_id!r}")
            if any(edge.source_id == node_id or edge.target_id == node_id for edge in graph.edges):
                return ValidationResult(
                    accepted=False,
                    reason=f"node {node_id!r} still has incident edges",
                )
            remaining_nodes = tuple(node for node in graph.nodes if node.node_id != node_id)
            CognitiveGraph(nodes=remaining_nodes, edges=graph.edges, kernel_limits=kernel_limits)
            return ValidationResult(accepted=True)
    except (GraphError, KeyError, TypeError, ValueError) as exc:
        return ValidationResult(accepted=False, reason=str(exc))

    return ValidationResult(accepted=False, reason=f"unsupported mutation kind {mutation.kind!r} in this version")


def apply_mutations(
    graph: CognitiveGraph, mutations: tuple[Mutation, ...], kernel_limits: KernelLimits, *, frozen: bool = False
) -> CognitiveGraph:
    """Apply a structural batch atomically.

    Every step is validated against the graph produced by the preceding
    step. If any mutation is invalid, the original graph is returned and no
    structural change from the batch becomes visible. This makes structural
    plasticity a data transaction rather than a sequence of partially
    committed edits. Node removal therefore requires all incident edges to
    have been removed by earlier mutations in the same batch.
    """
    if frozen or not mutations:
        return graph
    if len(mutations) > kernel_limits.max_structural_mutations_per_consolidation:
        return graph

    nodes = list(graph.nodes)
    edges = list(graph.edges)

    for mutation in mutations:
        candidate_graph = CognitiveGraph(nodes=tuple(nodes), edges=tuple(edges), kernel_limits=kernel_limits)
        result = validate_mutation(mutation, candidate_graph, kernel_limits)
        if not result.accepted:
            return graph

        if mutation.kind == "add_edge":
            edges.append(_edge_from_payload(mutation.payload))
        elif mutation.kind == "add_node":
            node = _node_from_payload(mutation.payload)
            nodes.append(node)
            for source_id in mutation.payload.get("source_ids", ()):
                edges.append(
                    PlasticEdge(
                        source_id=str(source_id),
                        target_id=node.node_id,
                        kind=EdgeKind.EXCITATORY,
                        weight=_TENTATIVE_INITIAL_WEIGHT,
                        plasticity=0.5,
                        delay_ticks=1,
                    )
                )
        elif mutation.kind == "remove_edge":
            key = _edge_key(mutation.payload)
            edges = [edge for edge in edges if (edge.source_id, edge.target_id, edge.kind) != key]
        elif mutation.kind == "remove_node":
            node_id = str(mutation.payload["node_id"])
            nodes = [node for node in nodes if node.node_id != node_id]
        elif mutation.kind == "quarantine_edge":
            # Quarantine is currently a derived lifecycle state, not stored
            # mutable state. Keeping this no-op explicit preserves the v0.58
            # API without pretending it changed topology.
            pass

    try:
        return CognitiveGraph(nodes=tuple(nodes), edges=tuple(edges), kernel_limits=kernel_limits)
    except GraphError:
        return graph


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
    mutation = Mutation(
        kind="add_node",
        payload={
            "node_id": new_concept_id,
            "kind": NodeKind.CONCEPT,
            "source_ids": candidate_node_ids,
        },
    )
    return mutation if validate_mutation(mutation, graph, kernel_limits).accepted else None


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
