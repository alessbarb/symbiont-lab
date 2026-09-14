from __future__ import annotations

import math
from dataclasses import dataclass
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
_ELIGIBILITY_THRESHOLD = 1e-6
_TENTATIVE_WEIGHT = 0.05
_CORE_READOUT_ID = "readout_core"


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


class CognitiveBridge:
    """Wire a CognitiveGraph into the organism's resident tick loop.

    Learning is local but no longer unconditional: the runtime may provide
    the SENSE nodes selected by attention plus bounded health/availability
    modulation for those senses. Only the forward subgraph reachable from
    attended senses can receive a full Oja update, eligibility must be
    non-zero, and each edge's own plasticity scales the update.

    A germinal graph may start empty. Mature opaque percept names supplied by
    the runtime are admitted as SENSE nodes within the genome's soft node
    budget. Repeated co-activation can then create the first latent concept
    and a semantics-free readout. Owner-authored non-empty graphs remain
    closed to implicit sense admission unless they explicitly opt in. Kernel
    hard limits remain outside learnable state and always dominate the
    genome's softer growth budgets.
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
        self._topology_revision = 0
        self._develop_senses = (not graph.nodes) if develop_senses is None else bool(develop_senses)
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        self._tracked_edge_keys: set[tuple[str, str, str]] = set()
        self._seed_new_edges()
        self._reacclimation_remaining = 0  # a first-ever construction never reacclimates (design §16a)

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
    def _soft_node_limit(self) -> int:
        return min(self._genome.development.soft_node_budget, self._kernel_limits.max_nodes)

    @property
    def _soft_edge_limit(self) -> int:
        return min(self._genome.development.soft_edge_budget, self._kernel_limits.max_edges)

    def _seed_new_edges(self) -> None:
        current_keys = {
            (edge.source_id, edge.target_id, edge.kind.value)
            for edge in self._graph.edges
        }
        self._weight_tracker.reconcile(current_keys)
        for edge in self._graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            if key in self._tracked_edge_keys:
                continue
            self._weight_tracker.seed(key, quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES))
        self._tracked_edge_keys = current_keys

    def _admit_senses(self, sense_values: Mapping[str, float]) -> None:
        """Materialize developed percepts as SENSE nodes for germinal graphs.

        Sensory identity admission is not a learned structural mutation: it is
        the bridge between the already-governed developmental sensor model and
        cognition. It is nevertheless bounded by both the genome soft budget
        and the kernel hard ceiling and advances topology_revision when the
        visible topology changes.
        """
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        existing_ids = {node.node_id for node in self._graph.nodes}
        candidates = sorted(set(sense_values) - existing_ids)
        if not candidates:
            return

        graph = self._graph
        admitted = 0
        for sense_id in candidates:
            if len(graph.nodes) >= self._soft_node_limit:
                break
            try:
                graph = CognitiveGraph(
                    nodes=(*graph.nodes, PlasticNode(node_id=sense_id, kind=NodeKind.SENSE)),
                    edges=graph.edges,
                    kernel_limits=self._kernel_limits,
                )
            except GraphError:
                # Runtime-generated names are valid by construction. An
                # invalid external/custom name is simply not admitted rather
                # than destabilising the resident loop.
                continue
            admitted += 1

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

    def _concept_signature_exists(self, source_ids: tuple[str, str]) -> bool:
        pair = set(source_ids)
        concept_ids = {
            node.node_id for node in self._graph.nodes if node.kind is NodeKind.CONCEPT
        }
        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
        for edge in self._graph.edges:
            if edge.target_id in incoming:
                incoming[edge.target_id].add(edge.source_id)
        return any(pair.issubset(sources) for sources in incoming.values())

    def _new_node_id(self, prefix: str) -> str:
        """Return a deterministic opaque local node id.

        IDs carry no host meaning and are derived only from already materialized
        graph occupancy, keeping laboratory replay deterministic while avoiding
        content-derived identifiers.
        """
        existing = {node.node_id for node in self._graph.nodes}
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
    ) -> tuple[Mutation, ...]:
        """Create at most one latent concept from repeated opaque co-activity.

        Candidate evidence is deliberately RAM-only, matching the existing
        structural-plasticity rule: only topology that actually crosses the
        consolidation boundary becomes durable. A newly born concept is wired
        from two senses and into one semantics-free readout so the empty birth
        graph can become behaviorally observable without owner-authored labels.
        """
        if not self._develop_senses or mutation_slots < 2 or node_slots < 1 or edge_slots < 3:
            return ()
        concept_count = sum(1 for node in self._graph.nodes if node.kind is NodeKind.CONCEPT)
        if concept_count >= self._kernel_limits.max_concepts:
            return ()

        eligible = sorted(
            (
                (support, pair)
                for pair, support in self._concept_support.items()
                if support >= self._genome.structure.minimum_support
                and not self._concept_signature_exists(pair)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return ()

        _, source_ids = eligible[0]
        node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
        if any(node_kinds.get(source_id) is not NodeKind.SENSE for source_id in source_ids):
            return ()

        readouts = sorted(
            node.node_id for node in self._graph.nodes if node.kind is NodeKind.READOUT
        )
        needs_readout = not readouts
        required_mutations = 3 if needs_readout else 2
        required_nodes = 2 if needs_readout else 1
        if mutation_slots < required_mutations or node_slots < required_nodes:
            return ()

        concept_id = self._new_node_id("concept")
        mutations: list[Mutation] = [
            Mutation(
                kind="add_node",
                payload={
                    "node_id": concept_id,
                    "kind": NodeKind.CONCEPT,
                    "source_ids": source_ids,
                },
            )
        ]

        if needs_readout:
            existing_ids = {node.node_id for node in self._graph.nodes}
            readout_id = _CORE_READOUT_ID if _CORE_READOUT_ID not in existing_ids else self._new_node_id("readout")
            mutations.append(
                Mutation(
                    kind="add_node",
                    payload={"node_id": readout_id, "kind": NodeKind.READOUT},
                )
            )
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

    def export_checkpoint(self) -> dict[str, object]:
        return {
            "graph": export_graph_checkpoint(self._graph, weight_class_overrides=self._weight_class_overrides()),
            "safety_state": export_safety_state(self._safety_state),
            "sensory_normalizers": export_sensory_normalizers(self._normalizers),
            "topology_revision": self._topology_revision,
            "develop_senses": self._develop_senses,
        }

    def _weight_class_overrides(self) -> dict[tuple[str, str, str], int]:
        return {
            (edge.source_id, edge.target_id, edge.kind.value): self._weight_tracker.durable_class(
                (edge.source_id, edge.target_id, edge.kind.value)
            )
            for edge in self._graph.edges
        }

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
        # Design §10.4: in-progress structural candidate/cooldown state is
        # RAM-only working memory, never checkpointed -- a restart always
        # starts structural plasticity fresh. Anything that had actually
        # crossed into real topology already survives via graph.nodes/edges.
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
        # previous_frame is labile (design §10.3, P5, P11) -- never restored;
        # bridge._previous_frame is already {} from cls(...)'s own __init__.
        raw_revision = payload.get("topology_revision", 0)
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 0:
            raise GraphError("topology_revision must be a non-negative integer")
        bridge._topology_revision = raw_revision
        bridge._reacclimation_remaining = kernel_limits.reacclimation_ticks
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

        self._admit_senses(sense_values)

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
            )

        self._safety_state.record_success()
        prediction_errors = compute_prediction_errors(
            self._graph, current=frame.activations, previous=self._previous_frame
        )

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
                used = abs(source_value) >= _ACTIVITY_THRESHOLD and abs(target_current) >= _ACTIVITY_THRESHOLD
                advance_edge_age(edge, tick=tick, used=used)

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

            active_nodes = [
                node_id for node_id, value in frame.activations.items() if abs(value) >= _ACTIVITY_THRESHOLD
            ]
            for index, source_id in enumerate(active_nodes):
                for target_id in active_nodes[index + 1 :]:
                    self._structural_plasticity.observe_coactivation(
                        source_id=source_id,
                        target_id=target_id,
                        source_active=True,
                        target_active=True,
                        tick=tick,
                    )
            self._record_concept_support(frame.activations)

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and self._reacclimation_remaining <= 0 and tick % interval == 0:
            mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation
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

            projected_edges = max(0, len(self._graph.edges) + self._edge_delta(prune_mutations))
            edge_slots = max(0, self._soft_edge_limit - projected_edges)
            node_slots = max(0, self._soft_node_limit - len(self._graph.nodes))
            concept_mutations = self._propose_germinal_concept_mutations(
                mutation_slots=remaining,
                node_slots=node_slots,
                edge_slots=edge_slots,
            )
            remaining -= len(concept_mutations)
            edge_slots = max(0, edge_slots - max(0, self._edge_delta(concept_mutations)))

            proposed = self._structural_plasticity.propose(
                self._graph,
                kernel_limits=self._kernel_limits,
                tick=tick,
                max_mutations=min(remaining, edge_slots),
            )
            all_mutations = prune_mutations + concept_mutations + proposed
            if all_mutations:
                candidate = apply_mutations(
                    self._graph, all_mutations, self._kernel_limits, frozen=frozen
                )
                if candidate is not self._graph:
                    self._graph = candidate
                    self._seed_new_edges()
                    structural_mutations_applied = len(all_mutations)
                    applied_mutations = all_mutations
                    self._topology_revision += 1
            self._structural_plasticity.reconcile({node.node_id for node in self._graph.nodes})

        self._previous_frame = dict(frame.activations)
        return CognitiveBridgeResult(
            tick=tick,
            activations=frame.activations,
            readouts=frame.readouts,
            prediction_errors=prediction_errors,
            structural_mutations_applied=structural_mutations_applied,
            frozen=frozen,
            topology_revision=self._topology_revision,
            consecutive_failures=self._safety_state.consecutive_failures,
            mutations=applied_mutations,
        )
