from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Collection, Mapping

from ..cognition.activation import SensoryNormalizer
from ..cognition.checkpoint import (
    WEIGHT_CLASSES,
    export_graph_checkpoint,
    export_safety_state,
    export_sensory_normalizers,
    quantize_signed,
    restore_graph_checkpoint,
    restore_safety_state,
    restore_sensory_normalizers,
)
from ..cognition.genome import Genome
from ..cognition.graph import CognitiveGraph, GraphError, PlasticNode, TickContext
from ..cognition.learning import PredictionError, apply_oja_update, compute_prediction_errors, update_eligibility
from ..cognition.limits import KernelLimits
from ..cognition.metaplasticity import SafetyState
from ..cognition.structure import (
    EdgeLifecycleState,
    Mutation,
    StructuralPlasticity,
    advance_edge_age,
    apply_mutations,
    evaluate_edge_lifecycle,
)
from ..cognition.types import WEIGHT_RANGE, EdgeKind, NodeKind
from .weight_stability import WeightStabilityTracker

_ACTIVITY_THRESHOLD = 0.1
_EDGE_USAGE_THRESHOLD = 1e-3
_ELIGIBILITY_THRESHOLD = 1e-6
_TENTATIVE_WEIGHT = 0.05
_CORE_READOUT_ID = "readout_core"


class TopologyHealth(StrEnum):
    GERMINAL = "germinal"
    DEVELOPING = "developing"
    CONNECTED = "connected"
    ADAPTIVE = "adaptive"
    DEGENERATE = "degenerate"
    RECOVERING = "recovering"


@dataclass(slots=True, frozen=True)
class ConceptLineage:
    concept_id: str
    parent_ids: tuple[str, ...]
    born_tick: int


@dataclass(slots=True, frozen=True)
class CognitiveBridgeResult:
    tick: int
    activations: Mapping[str, float]
    readouts: Mapping[str, float]
    prediction_errors: tuple[PredictionError, ...]
    structural_mutations_applied: int
    frozen: bool
    topology_revision: int
    consecutive_failures: int = 0
    mutations: tuple[Mutation, ...] = ()
    topology_health: TopologyHealth = TopologyHealth.GERMINAL
    recovering: bool = False


class CognitiveBridge:
    """Wire a CognitiveGraph into the organism's resident tick loop.

    Germinal cognition follows a reversible homeostatic cycle: observe and
    learn, maintain weak/obsolete structure, reclaim node capacity, then grow
    new structure, with the entire structural batch committed atomically.
    Structural validity is complemented by a derived topology-health state so
    a syntactically valid but developmentally trapped graph can enter recovery.

    Owner-authored non-empty graphs remain outside automatic sense admission,
    node GC, sensory eviction and topology recovery unless they explicitly opt
    into ``develop_senses``.
    """

    def __init__(
        self,
        *,
        graph: CognitiveGraph,
        genome: Genome,
        kernel_limits: KernelLimits,
        structural_plasticity: StructuralPlasticity | None = None,
        safety_state: SafetyState | None = None,
        develop_senses: bool | None = None,
    ) -> None:
        self._graph = graph
        self._genome = genome
        self._kernel_limits = kernel_limits
        self._structural_plasticity = (
            structural_plasticity
            if structural_plasticity is not None
            else StructuralPlasticity(
                min_candidate_support=genome.structure.minimum_support,
                tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
                cooldown_ticks=genome.structure.tentative_lifetime_ticks,
            )
        )
        self._safety_state = safety_state if safety_state is not None else SafetyState()
        self._normalizers: dict[str, SensoryNormalizer] = {}
        self._previous_frame: dict[str, float] = {}
        self._concept_support: dict[tuple[str, str], int] = {}
        self._concept_lineage: dict[str, ConceptLineage] = {}
        self._sense_last_seen_tick: dict[str, int] = {}
        self._orphan_since_tick: dict[str, int] = {}
        self._topology_revision = 0
        self._develop_senses = (not graph.nodes) if develop_senses is None else bool(develop_senses)
        self._recovery_pending = False
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        self._tracked_edge_keys: set[tuple[str, str, str]] = set()
        self._seed_new_edges()
        self._reacclimation_remaining = 0

    @property
    def graph(self) -> CognitiveGraph:
        return self._graph

    @property
    def safety_state(self) -> SafetyState:
        return self._safety_state

    @property
    def topology_revision(self) -> int:
        return self._topology_revision

    @property
    def develop_senses(self) -> bool:
        return self._develop_senses

    @property
    def recovery_pending(self) -> bool:
        return self._recovery_pending

    @property
    def concept_lineage(self) -> tuple[ConceptLineage, ...]:
        return tuple(self._concept_lineage[key] for key in sorted(self._concept_lineage))

    @property
    def topology_health(self) -> TopologyHealth:
        return self._classify_topology_health()

    @property
    def _soft_node_limit(self) -> int:
        return min(self._genome.development.soft_node_budget, self._kernel_limits.max_nodes)

    @property
    def _sense_node_limit(self) -> int:
        return min(self._genome.development.sense_node_budget, self._soft_node_limit)

    @property
    def _soft_edge_limit(self) -> int:
        return min(self._genome.development.soft_edge_budget, self._kernel_limits.max_edges)

    def _seed_new_edges(self) -> None:
        current_keys = {(edge.source_id, edge.target_id, edge.kind.value) for edge in self._graph.edges}
        self._weight_tracker.reconcile(current_keys)
        for edge in self._graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            if key in self._tracked_edge_keys:
                continue
            self._weight_tracker.seed(key, quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES))
        self._tracked_edge_keys = current_keys

    def _admit_senses(self, sense_values: Mapping[str, float], *, tick: int) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        existing_ids = {node.node_id for node in self._graph.nodes}
        existing_senses = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.SENSE}
        for sense_id in set(sense_values) & existing_senses:
            self._sense_last_seen_tick[sense_id] = tick

        candidates = sorted(set(sense_values) - existing_ids)
        if not candidates:
            return

        graph = self._graph
        admitted = 0
        sense_count = len(existing_senses)
        for sense_id in candidates:
            if len(graph.nodes) >= self._soft_node_limit or sense_count >= self._sense_node_limit:
                break
            try:
                graph = CognitiveGraph(
                    nodes=(*graph.nodes, PlasticNode(node_id=sense_id, kind=NodeKind.SENSE)),
                    edges=graph.edges,
                    kernel_limits=self._kernel_limits,
                )
            except GraphError:
                continue
            admitted += 1
            sense_count += 1
            self._sense_last_seen_tick[sense_id] = tick

        if admitted:
            self._graph = graph
            self._topology_revision += 1

    def _record_concept_support(self, activations: Mapping[str, float]) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        kinds = {node.node_id: node.kind for node in self._graph.nodes}
        threshold = max(_ACTIVITY_THRESHOLD, self._genome.structure.grow_threshold)
        active_senses = sorted(
            node_id
            for node_id, value in activations.items()
            if kinds.get(node_id) is NodeKind.SENSE and abs(value) >= threshold
        )
        for index, source_id in enumerate(active_senses):
            for target_id in active_senses[index + 1 :]:
                key = (source_id, target_id)
                self._concept_support[key] = self._concept_support.get(key, 0) + 1

    def _concept_signature_exists(
        self, source_ids: tuple[str, str], *, graph: CognitiveGraph | None = None
    ) -> bool:
        pair = set(source_ids)
        if any(pair.issubset(set(lineage.parent_ids)) for lineage in self._concept_lineage.values()):
            return True
        active_graph = self._graph if graph is None else graph
        concept_ids = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.CONCEPT}
        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
        for edge in active_graph.edges:
            if edge.target_id in incoming:
                incoming[edge.target_id].add(edge.source_id)
        return any(pair.issubset(sources) for sources in incoming.values())

    def _new_node_id(self, prefix: str, *, graph: CognitiveGraph | None = None) -> str:
        active_graph = self._graph if graph is None else graph
        existing = {node.node_id for node in active_graph.nodes}
        index = 1
        while True:
            candidate = f"{prefix}_{index:016x}"
            if candidate not in existing:
                return candidate
            index += 1

    def _propose_germinal_concept_mutations(
        self,
        *,
        mutation_slots: int,
        node_slots: int,
        edge_slots: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        active_graph = self._graph if graph is None else graph
        if not self._develop_senses or mutation_slots < 2 or node_slots < 1 or edge_slots < 3:
            return ()
        concept_count = sum(1 for node in active_graph.nodes if node.kind is NodeKind.CONCEPT)
        if concept_count >= self._kernel_limits.max_concepts:
            return ()

        eligible = sorted(
            (
                (support, pair)
                for pair, support in self._concept_support.items()
                if support >= self._genome.structure.minimum_support
                and not self._concept_signature_exists(pair, graph=active_graph)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return ()

        _, source_ids = eligible[0]
        node_kinds = {node.node_id: node.kind for node in active_graph.nodes}
        if any(node_kinds.get(source_id) is not NodeKind.SENSE for source_id in source_ids):
            return ()

        readouts = sorted(node.node_id for node in active_graph.nodes if node.kind is NodeKind.READOUT)
        needs_readout = not readouts
        required_mutations = 3 if needs_readout else 2
        required_nodes = 2 if needs_readout else 1
        if mutation_slots < required_mutations or node_slots < required_nodes:
            return ()

        concept_id = self._new_node_id("concept", graph=active_graph)
        mutations: list[Mutation] = [
            Mutation(
                kind="add_node",
                payload={"node_id": concept_id, "kind": NodeKind.CONCEPT, "source_ids": source_ids},
            )
        ]
        if needs_readout:
            existing_ids = {node.node_id for node in active_graph.nodes}
            readout_id = (
                _CORE_READOUT_ID
                if _CORE_READOUT_ID not in existing_ids
                else self._new_node_id("readout", graph=active_graph)
            )
            mutations.append(Mutation(kind="add_node", payload={"node_id": readout_id, "kind": NodeKind.READOUT}))
        else:
            readout_id = readouts[0]
        mutations.append(
            Mutation(
                kind="add_edge",
                payload={
                    "source_id": concept_id,
                    "target_id": readout_id,
                    "kind": EdgeKind.EXCITATORY,
                    "weight": _TENTATIVE_WEIGHT,
                    "plasticity": 0.5,
                    "delay_ticks": 1,
                },
            )
        )
        return tuple(mutations)

    def _orphan_latent_ids(self, graph: CognitiveGraph | None = None) -> set[str]:
        active_graph = self._graph if graph is None else graph
        incident = {node.node_id: 0 for node in active_graph.nodes}
        for edge in active_graph.edges:
            incident[edge.source_id] = incident.get(edge.source_id, 0) + 1
            incident[edge.target_id] = incident.get(edge.target_id, 0) + 1
        return {
            node.node_id
            for node in active_graph.nodes
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT) and incident.get(node.node_id, 0) == 0
        }

    def _orphan_node_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        orphan_ids = self._orphan_latent_ids(active_graph)
        for node in active_graph.nodes:
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT) and node.node_id not in orphan_ids:
                self._orphan_since_tick.pop(node.node_id, None)

        grace = max(1, self._genome.structure.tentative_lifetime_ticks)
        mutations: list[Mutation] = []
        for node_id in sorted(orphan_ids):
            since = self._orphan_since_tick.setdefault(node_id, tick)
            if tick - since < grace:
                continue
            mutations.append(Mutation(kind="remove_node", payload={"node_id": node_id}))
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    def _sense_eviction_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        senses = [node for node in active_graph.nodes if node.kind is NodeKind.SENSE]
        if not senses:
            return ()
        incident_ids = {node_id for edge in active_graph.edges for node_id in (edge.source_id, edge.target_id)}
        over_budget = max(0, len(senses) - self._sense_node_limit)
        retention = max(1, self._genome.development.sense_retention_ticks)
        candidates: list[tuple[bool, int, str]] = []
        for node in senses:
            if node.node_id in incident_ids:
                continue
            last_seen = self._sense_last_seen_tick.get(node.node_id, 0)
            stale = tick - last_seen >= retention
            candidates.append((stale, last_seen, node.node_id))

        candidates.sort(key=lambda item: (not item[0], item[1], item[2]))
        mutations: list[Mutation] = []
        needed_over_budget = over_budget
        for stale, _, node_id in candidates:
            if not stale and needed_over_budget <= 0:
                continue
            mutations.append(Mutation(kind="remove_node", payload={"node_id": node_id}))
            if needed_over_budget > 0:
                needed_over_budget -= 1
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    def _has_sense_to_readout_path(
        self, graph: CognitiveGraph | None = None, *, established_only: bool = False
    ) -> bool:
        active_graph = self._graph if graph is None else graph
        senses = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.SENSE}
        readouts = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.READOUT}
        if not senses or not readouts:
            return False
        adjacency: dict[str, set[str]] = {}
        for edge in active_graph.edges:
            if established_only and edge.support < self._genome.structure.minimum_support:
                continue
            adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        frontier = list(senses)
        visited = set(senses)
        while frontier:
            source_id = frontier.pop()
            for target_id in adjacency.get(source_id, ()):
                if target_id in readouts:
                    return True
                if target_id not in visited:
                    visited.add(target_id)
                    frontier.append(target_id)
        return False

    def _classify_topology_health(
        self,
        graph: CognitiveGraph | None = None,
        *,
        include_recovery: bool = True,
    ) -> TopologyHealth:
        active_graph = self._graph if graph is None else graph
        if include_recovery and self._recovery_pending:
            return TopologyHealth.RECOVERING
        if not active_graph.nodes:
            return TopologyHealth.GERMINAL
        if self._has_sense_to_readout_path(active_graph, established_only=True):
            return TopologyHealth.ADAPTIVE
        if self._has_sense_to_readout_path(active_graph):
            return TopologyHealth.CONNECTED

        latent_nodes = [node for node in active_graph.nodes if node.kind is not NodeKind.SENSE]
        sense_count = sum(1 for node in active_graph.nodes if node.kind is NodeKind.SENSE)
        if self._develop_senses and sense_count > self._sense_node_limit:
            return TopologyHealth.DEGENERATE
        if not latent_nodes:
            return TopologyHealth.GERMINAL if self._develop_senses else TopologyHealth.DEVELOPING
        if self._develop_senses:
            node_budget_full = len(active_graph.nodes) >= self._soft_node_limit
            no_edges_with_latent = not active_graph.edges
            if no_edges_with_latent or node_budget_full:
                return TopologyHealth.DEGENERATE
        return TopologyHealth.DEVELOPING

    def _hard_deadlock_signature(self) -> bool:
        if not self._develop_senses or self._graph.edges:
            return False
        latent = any(node.kind is not NodeKind.SENSE for node in self._graph.nodes)
        return latent and len(self._graph.nodes) >= self._soft_node_limit

    def _enter_recovery_if_needed(self, *, prime_legacy_deadlock: bool = False) -> None:
        if not self._develop_senses or self._recovery_pending:
            return
        if self._classify_topology_health(include_recovery=False) is not TopologyHealth.DEGENERATE:
            return
        self._recovery_pending = True
        if prime_legacy_deadlock and self._hard_deadlock_signature():
            for node_id in self._orphan_latent_ids():
                self._orphan_since_tick.setdefault(node_id, 0)

    def _refresh_recovery_state(self) -> None:
        if not self._recovery_pending:
            return
        if self._classify_topology_health(include_recovery=False) is not TopologyHealth.DEGENERATE:
            self._recovery_pending = False

    @staticmethod
    def _edge_delta(mutations: Collection[Mutation]) -> int:
        delta = 0
        for mutation in mutations:
            if mutation.kind == "add_edge":
                delta += 1
            elif mutation.kind == "remove_edge":
                delta -= 1
            elif mutation.kind == "add_node":
                delta += len(tuple(mutation.payload.get("source_ids", ())))
        return delta

    def _record_applied_metadata(self, mutations: Collection[Mutation], *, tick: int) -> None:
        for mutation in mutations:
            if mutation.kind == "add_node":
                try:
                    kind = NodeKind(mutation.payload["kind"])
                except (KeyError, TypeError, ValueError):
                    continue
                node_id = str(mutation.payload.get("node_id", ""))
                if kind is NodeKind.CONCEPT:
                    parent_ids = tuple(sorted(str(value) for value in mutation.payload.get("source_ids", ())))
                    if parent_ids:
                        self._concept_lineage[node_id] = ConceptLineage(node_id, parent_ids, tick)
            elif mutation.kind == "remove_node":
                node_id = str(mutation.payload.get("node_id", ""))
                self._concept_lineage.pop(node_id, None)
                self._sense_last_seen_tick.pop(node_id, None)
                self._orphan_since_tick.pop(node_id, None)
                self._normalizers.pop(node_id, None)

    def _reconcile_node_metadata(self) -> None:
        node_ids = {node.node_id for node in self._graph.nodes}
        sense_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.SENSE}
        concept_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.CONCEPT}
        latent_ids = {
            node.node_id
            for node in self._graph.nodes
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT)
        }
        self._sense_last_seen_tick = {key: value for key, value in self._sense_last_seen_tick.items() if key in sense_ids}
        self._concept_lineage = {key: value for key, value in self._concept_lineage.items() if key in concept_ids}
        self._orphan_since_tick = {key: value for key, value in self._orphan_since_tick.items() if key in latent_ids}
        self._normalizers = {key: value for key, value in self._normalizers.items() if key in sense_ids}
        self._concept_support = {
            pair: count
            for pair, count in self._concept_support.items()
            if pair[0] in sense_ids and pair[1] in sense_ids
        }
        self._structural_plasticity.reconcile(node_ids)

    def export_checkpoint(self) -> dict[str, object]:
        return {
            "graph": export_graph_checkpoint(self._graph, weight_class_overrides=self._weight_class_overrides()),
            "safety_state": export_safety_state(self._safety_state),
            "sensory_normalizers": export_sensory_normalizers(self._normalizers),
            "topology_revision": self._topology_revision,
            "develop_senses": self._develop_senses,
            "concept_lineage": [
                {"concept_id": x.concept_id, "parent_ids": list(x.parent_ids), "born_tick": x.born_tick}
                for x in self.concept_lineage
            ],
            "sense_last_seen_tick": dict(sorted(self._sense_last_seen_tick.items())),
            "orphan_since_tick": dict(sorted(self._orphan_since_tick.items())),
            "recovery_pending": self._recovery_pending,
        }

    def _weight_class_overrides(self) -> dict[tuple[str, str, str], int]:
        return {
            (edge.source_id, edge.target_id, edge.kind.value): self._weight_tracker.durable_class(
                (edge.source_id, edge.target_id, edge.kind.value)
            )
            for edge in self._graph.edges
        }

    @staticmethod
    def _restore_nonnegative_tick_map(
        payload: object, *, allowed_ids: Collection[str], field: str
    ) -> dict[str, int]:
        if payload is None:
            return {}
        if not isinstance(payload, Mapping):
            raise GraphError(f"{field} must be an object")
        allowed = set(allowed_ids)
        restored: dict[str, int] = {}
        for raw_id, raw_tick in payload.items():
            node_id = str(raw_id)
            if node_id not in allowed:
                continue
            if isinstance(raw_tick, bool) or not isinstance(raw_tick, int) or raw_tick < 0:
                raise GraphError(f"{field} values must be non-negative integers")
            restored[node_id] = raw_tick
        return restored

    @classmethod
    def _restore_concept_lineage(
        cls, payload: object, *, graph: CognitiveGraph, kernel_limits: KernelLimits
    ) -> dict[str, ConceptLineage]:
        concept_ids = {node.node_id for node in graph.nodes if node.kind is NodeKind.CONCEPT}
        restored: dict[str, ConceptLineage] = {}
        if payload is not None:
            if not isinstance(payload, list):
                raise GraphError("concept_lineage must be a list")
            if len(payload) > kernel_limits.max_concepts:
                raise GraphError("concept_lineage exceeds kernel concept bound")
            for entry in payload:
                if not isinstance(entry, Mapping):
                    raise GraphError("concept_lineage entries must be objects")
                concept_id = str(entry.get("concept_id", ""))
                if concept_id not in concept_ids or concept_id in restored:
                    continue
                raw_parents = entry.get("parent_ids")
                if not isinstance(raw_parents, list) or not 2 <= len(raw_parents) <= 4:
                    raise GraphError("concept_lineage.parent_ids must contain 2 to 4 ids")
                parent_ids = tuple(str(value) for value in raw_parents)
                if len(set(parent_ids)) != len(parent_ids):
                    raise GraphError("concept_lineage.parent_ids must be unique")
                born_tick = entry.get("born_tick")
                if isinstance(born_tick, bool) or not isinstance(born_tick, int) or born_tick < 0:
                    raise GraphError("concept_lineage.born_tick must be a non-negative integer")
                restored[concept_id] = ConceptLineage(concept_id, parent_ids, born_tick)

        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
        for edge in graph.edges:
            if edge.target_id in incoming:
                incoming[edge.target_id].add(edge.source_id)
        for concept_id, parents in incoming.items():
            if concept_id not in restored and len(parents) >= 2:
                restored[concept_id] = ConceptLineage(concept_id, tuple(sorted(parents))[:4], 0)
        return restored

    @classmethod
    def restore(
        cls, payload: dict[str, object] | None, *, genome: Genome, kernel_limits: KernelLimits
    ) -> "CognitiveBridge | None":
        if payload is None:
            return None
        graph = restore_graph_checkpoint(payload.get("graph"), kernel_limits=kernel_limits)
        if graph is None:
            return None
        safety_state = restore_safety_state(payload.get("safety_state"))
        structural_plasticity = StructuralPlasticity(
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
        )
        raw_develop_senses = payload.get("develop_senses")
        if raw_develop_senses is None:
            develop_senses = not graph.nodes
        elif not isinstance(raw_develop_senses, bool):
            raise GraphError("develop_senses must be a boolean")
        else:
            develop_senses = raw_develop_senses
        bridge = cls(
            graph=graph,
            genome=genome,
            kernel_limits=kernel_limits,
            structural_plasticity=structural_plasticity,
            safety_state=safety_state,
            develop_senses=develop_senses,
        )
        bridge._normalizers = restore_sensory_normalizers(payload.get("sensory_normalizers"))
        bridge._concept_lineage = cls._restore_concept_lineage(
            payload.get("concept_lineage"), graph=graph, kernel_limits=kernel_limits
        )
        sense_ids = {node.node_id for node in graph.nodes if node.kind is NodeKind.SENSE}
        latent_ids = {
            node.node_id
            for node in graph.nodes
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT)
        }
        bridge._sense_last_seen_tick = cls._restore_nonnegative_tick_map(
            payload.get("sense_last_seen_tick"), allowed_ids=sense_ids, field="sense_last_seen_tick"
        )
        bridge._orphan_since_tick = cls._restore_nonnegative_tick_map(
            payload.get("orphan_since_tick"), allowed_ids=latent_ids, field="orphan_since_tick"
        )
        raw_recovery = payload.get("recovery_pending", False)
        if not isinstance(raw_recovery, bool):
            raise GraphError("recovery_pending must be a boolean")
        bridge._recovery_pending = raw_recovery
        raw_revision = payload.get("topology_revision", 0)
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 0:
            raise GraphError("topology_revision must be a non-negative integer")
        bridge._topology_revision = raw_revision
        bridge._reacclimation_remaining = kernel_limits.reacclimation_ticks
        bridge._reconcile_node_metadata()
        bridge._enter_recovery_if_needed(prime_legacy_deadlock=True)
        return bridge

    def _learning_nodes(self, attended_sense_ids: Collection[str] | None) -> set[str]:
        node_ids = {node.node_id for node in self._graph.nodes}
        if attended_sense_ids is None:
            return node_ids
        reachable = set(attended_sense_ids) & node_ids
        changed = True
        while changed:
            changed = False
            for edge in self._graph.edges:
                if edge.source_id in reachable and edge.target_id not in reachable:
                    reachable.add(edge.target_id)
                    changed = True
        return reachable

    @staticmethod
    def _tick_modulation(
        attended_sense_ids: Collection[str] | None,
        sense_modulation: Mapping[str, float] | None,
    ) -> float:
        if attended_sense_ids is None or sense_modulation is None:
            return 1.0
        values = []
        for sense_id in attended_sense_ids:
            raw = sense_modulation.get(sense_id, 0.0)
            if math.isfinite(raw):
                values.append(max(0.0, min(1.0, float(raw))))
        return sum(values) / len(values) if values else 0.0

    def tick(
        self,
        sense_values: Mapping[str, float],
        *,
        tick: int,
        attended_sense_ids: Collection[str] | None = None,
        sense_modulation: Mapping[str, float] | None = None,
    ) -> CognitiveBridgeResult:
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1

        self._admit_senses(sense_values, tick=tick)
        self._enter_recovery_if_needed()

        sense_inputs: dict[str, float] = {}
        for node in self._graph.nodes:
            if node.kind is not NodeKind.SENSE:
                continue
            raw = sense_values.get(node.node_id)
            if raw is None:
                continue
            normalizer = self._normalizers.setdefault(node.node_id, SensoryNormalizer())
            sense_inputs[node.node_id] = normalizer.normalize(raw)

        try:
            frame = self._graph.activate(sense_inputs, TickContext(tick=tick), previous=self._previous_frame)
        except GraphError:
            self._safety_state.record_failure()
            return CognitiveBridgeResult(
                tick=tick,
                activations=dict(self._previous_frame),
                readouts={},
                prediction_errors=(),
                structural_mutations_applied=0,
                frozen=self._safety_state.frozen,
                topology_revision=self._topology_revision,
                consecutive_failures=self._safety_state.consecutive_failures,
                mutations=(),
                topology_health=self.topology_health,
                recovering=self._recovery_pending,
            )

        self._safety_state.record_success()
        prediction_errors = compute_prediction_errors(self._graph, current=frame.activations, previous=self._previous_frame)

        frozen = self._safety_state.frozen
        learning_nodes = self._learning_nodes(attended_sense_ids)
        tick_modulation = self._tick_modulation(attended_sense_ids, sense_modulation)
        if not frozen:
            for edge in self._graph.edges:
                source_value = (
                    sense_inputs.get(edge.source_id, 0.0)
                    if edge.delay_ticks == 0
                    else self._previous_frame.get(edge.source_id, 0.0)
                )
                target_current = frame.activations.get(edge.target_id, 0.0)
                update_eligibility(
                    edge,
                    source_previous=source_value,
                    target_current=target_current,
                    decay=self._genome.plasticity.eligibility_decay,
                )
                eligible = (
                    edge.source_id in learning_nodes
                    and edge.target_id in learning_nodes
                    and abs(edge.eligibility) >= _ELIGIBILITY_THRESHOLD
                )
                apply_oja_update(
                    edge,
                    source_activation=source_value,
                    target_activation=target_current,
                    learning_rate=self._genome.plasticity.learning_rate.initial,
                    modulation=tick_modulation * edge.plasticity,
                    eligible=eligible,
                    frozen=frozen,
                )
                transmitted = edge.weight * source_value
                advance_edge_age(edge, tick=tick, used=abs(transmitted) >= _EDGE_USAGE_THRESHOLD)

            edges_by_target: dict[str, list] = {}
            for edge in self._graph.edges:
                key = (edge.source_id, edge.target_id, edge.kind.value)
                self._weight_tracker.observe(key, quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES), tick=tick)
                edges_by_target.setdefault(edge.target_id, []).append(edge)
            for target_edges in edges_by_target.values():
                keys = [(edge.source_id, edge.target_id, edge.kind.value) for edge in target_edges]
                live_weights = {key: edge.weight for key, edge in zip(keys, target_edges)}
                self._weight_tracker.consolidate_node(
                    keys, live_weights, max_incoming_norm=self._kernel_limits.max_incoming_consolidated_weight_norm
                )

            node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
            active_nodes = [node_id for node_id, value in frame.activations.items() if abs(value) >= _ACTIVITY_THRESHOLD]
            for index, source_id in enumerate(active_nodes):
                for target_id in active_nodes[index + 1 :]:
                    self._structural_plasticity.observe_coactivation(
                        source_id=source_id,
                        target_id=target_id,
                        source_active=True,
                        target_active=True,
                        tick=tick,
                        source_kind=node_kinds.get(source_id),
                        target_kind=node_kinds.get(target_id),
                    )
            self._record_concept_support(frame.activations)

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and self._reacclimation_remaining <= 0 and tick % interval == 0:
            mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation

            # Maintenance is planned sequentially but committed only once:
            # prune edges -> GC newly/previously orphaned latent nodes -> evict
            # disconnected senses. Each stage sees the topology produced by
            # the previous stage, so pruning can begin an orphan grace period
            # immediately without exposing a partial graph.
            prune_candidates = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={"source_id": edge.source_id, "target_id": edge.target_id, "kind": edge.kind},
                )
                for edge in self._graph.edges
                if evaluate_edge_lifecycle(
                    edge,
                    current_tick=tick,
                    prune_threshold=self._genome.structure.prune_threshold,
                    minimum_support=self._genome.structure.minimum_support,
                    quarantine_window_ticks=self._genome.structure.tentative_lifetime_ticks,
                    tentative_lifetime_ticks=self._genome.structure.tentative_lifetime_ticks,
                )
                is EdgeLifecycleState.REMOVED
            )
            prune_mutations = prune_candidates[:mutation_cap]
            remaining = mutation_cap - len(prune_mutations)
            after_prune = apply_mutations(self._graph, prune_mutations, self._kernel_limits, frozen=frozen)
            if prune_mutations and after_prune is self._graph:
                prune_mutations = ()
                remaining = mutation_cap
                after_prune = self._graph

            orphan_mutations = self._orphan_node_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_prune,
            )
            remaining -= len(orphan_mutations)
            after_orphans = apply_mutations(after_prune, orphan_mutations, self._kernel_limits, frozen=frozen)
            if orphan_mutations and after_orphans is after_prune:
                orphan_mutations = ()
                remaining = mutation_cap - len(prune_mutations)
                after_orphans = after_prune

            sense_evictions = self._sense_eviction_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_orphans,
            )
            remaining -= len(sense_evictions)
            planning_graph = apply_mutations(after_orphans, sense_evictions, self._kernel_limits, frozen=frozen)
            if sense_evictions and planning_graph is after_orphans:
                sense_evictions = ()
                remaining = mutation_cap - len(prune_mutations) - len(orphan_mutations)
                planning_graph = after_orphans

            maintenance_mutations = prune_mutations + orphan_mutations + sense_evictions

            # Growth is planned against the reclaimed budget: concepts first,
            # then generic legal edges.
            edge_slots = max(0, self._soft_edge_limit - len(planning_graph.edges))
            node_slots = max(0, self._soft_node_limit - len(planning_graph.nodes))
            concept_mutations = self._propose_germinal_concept_mutations(
                mutation_slots=remaining,
                node_slots=node_slots,
                edge_slots=edge_slots,
                graph=planning_graph,
            )
            remaining -= len(concept_mutations)
            planning_after_concepts = apply_mutations(
                planning_graph, concept_mutations, self._kernel_limits, frozen=frozen
            )
            edge_slots = max(0, self._soft_edge_limit - len(planning_after_concepts.edges))
            proposed = self._structural_plasticity.propose(
                planning_after_concepts,
                kernel_limits=self._kernel_limits,
                tick=tick,
                max_mutations=min(remaining, edge_slots),
            )

            # The complete maintenance+growth transaction is committed against
            # the original graph. Any invalid step rolls the whole batch back.
            all_mutations = maintenance_mutations + concept_mutations + proposed
            if all_mutations:
                candidate = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                if candidate is not self._graph:
                    self._graph = candidate
                    self._record_applied_metadata(all_mutations, tick=tick)
                    self._seed_new_edges()
                    self._reconcile_node_metadata()
                    structural_mutations_applied = len(all_mutations)
                    applied_mutations = all_mutations
                    self._topology_revision += 1
            else:
                self._reconcile_node_metadata()
            self._refresh_recovery_state()
            self._enter_recovery_if_needed()

        live_node_ids = {node.node_id for node in self._graph.nodes}
        self._previous_frame = {node_id: value for node_id, value in frame.activations.items() if node_id in live_node_ids}
        return CognitiveBridgeResult(
            tick=tick,
            activations={node_id: value for node_id, value in frame.activations.items() if node_id in live_node_ids},
            readouts={node_id: value for node_id, value in frame.readouts.items() if node_id in live_node_ids},
            prediction_errors=prediction_errors,
            structural_mutations_applied=structural_mutations_applied,
            frozen=frozen,
            topology_revision=self._topology_revision,
            consecutive_failures=self._safety_state.consecutive_failures,
            mutations=applied_mutations,
            topology_health=self.topology_health,
            recovering=self._recovery_pending,
        )
