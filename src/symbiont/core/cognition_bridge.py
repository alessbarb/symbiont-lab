from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..cognition.activation import SensoryNormalizer
from ..cognition.checkpoint import (
    export_activation_frame,
    export_graph_checkpoint,
    export_safety_state,
    export_sensory_normalizers,
    restore_activation_frame,
    restore_graph_checkpoint,
    restore_safety_state,
    restore_sensory_normalizers,
)
from ..cognition.genome import Genome
from ..cognition.graph import CognitiveGraph, GraphError, TickContext
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
from ..cognition.types import NodeKind

_ACTIVITY_THRESHOLD = 0.1


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

    The bridge now persists every piece of cognitive state required for
    restart continuity: learned graph state, safety state, established
    sensory normalizers, the quantized previous activation frame consumed by
    delay=1 edges, and abstract structural-plasticity support/cooldowns.
    Checkpointing still never stores raw host readings.

    Eligibility gating remains unconditional rather than attention-selected,
    and metaplasticity is not yet wired because the runtime still lacks a
    sound full LearningObjective for comparable windows.
    """

    def __init__(
        self,
        *,
        graph: CognitiveGraph,
        genome: Genome,
        kernel_limits: KernelLimits,
        structural_plasticity: StructuralPlasticity | None = None,
        safety_state: SafetyState | None = None,
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
        self._topology_revision = 0

    @property
    def graph(self) -> CognitiveGraph:
        return self._graph

    @property
    def safety_state(self) -> SafetyState:
        return self._safety_state

    def export_checkpoint(self) -> dict[str, object]:
        return {
            "graph": export_graph_checkpoint(self._graph),
            "safety_state": export_safety_state(self._safety_state),
            "sensory_normalizers": export_sensory_normalizers(self._normalizers),
            "previous_frame": export_activation_frame(self._previous_frame),
            "structural_plasticity": self._structural_plasticity.export_checkpoint(),
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
        allowed_node_ids = {node.node_id for node in graph.nodes}
        structural_plasticity = StructuralPlasticity.restore_checkpoint(
            payload.get("structural_plasticity"),
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
            allowed_node_ids=allowed_node_ids,
        )
        bridge = cls(
            graph=graph,
            genome=genome,
            kernel_limits=kernel_limits,
            structural_plasticity=structural_plasticity,
            safety_state=safety_state,
        )
        bridge._normalizers = restore_sensory_normalizers(payload.get("sensory_normalizers"))
        restored_previous = restore_activation_frame(payload.get("previous_frame"))
        bridge._previous_frame = {
            node_id: value for node_id, value in restored_previous.items() if node_id in allowed_node_ids
        }
        return bridge

    def tick(self, sense_values: Mapping[str, float], *, tick: int) -> CognitiveBridgeResult:
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
                apply_oja_update(
                    edge,
                    source_activation=source_value,
                    target_activation=target_current,
                    learning_rate=self._genome.plasticity.learning_rate.initial,
                    modulation=1.0,
                    eligible=True,
                    frozen=frozen,
                )
                used = abs(source_value) >= _ACTIVITY_THRESHOLD and abs(target_current) >= _ACTIVITY_THRESHOLD
                advance_edge_age(edge, tick=tick, used=used)

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

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and tick % interval == 0:
            proposed = self._structural_plasticity.propose(
                self._graph, kernel_limits=self._kernel_limits, tick=tick
            )
            prune_mutations = tuple(
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
            all_mutations = proposed + prune_mutations
            if all_mutations:
                self._graph = apply_mutations(
                    self._graph, all_mutations, self._kernel_limits, frozen=frozen
                )
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
