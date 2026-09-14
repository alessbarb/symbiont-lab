from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..cognition.activation import SensoryNormalizer
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


class CognitiveBridge:
    """Wires a CognitiveGraph into the organism's tick loop: sensory
    normalization -> activation -> label-free learning (eligibility +
    bounded Oja) -> bounded structural plasticity, all gated by a
    SafetyState that freezes the plastic network -- never perception or
    checkpointing -- after 3 consecutive tick failures (master doc §13
    invariant 9). Genome-driven initial graph topology stays out of
    scope (v0.56's own disclosed non-goal, unspecified in the master
    doc); the graph itself is caller-supplied.

    Not yet wired here (disclosed gaps, not silent omissions):
    - Graph structural state (nodes/edges/weights) is not persisted
      through OrganismRuntime's checkpoint -- only genome identity is.
    - Eligibility gating is unconditional (every edge, every tick),
      not yet attention-selected as master doc §6.3 describes -- there
      is no existing mechanism mapping host attention allocations onto
      graph edges to build on yet.
    - Metaplasticity (MetaParameter self-tuning) is not wired -- it
      needs a real LearningObjective computed from two comparable
      windows, including information_retained/calibration dimensions
      this integration has no sound way to compute yet without
      fabricating a number; wiring it with a fake metric would be
      worse than not wiring it.
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

    @property
    def graph(self) -> CognitiveGraph:
        return self._graph

    @property
    def safety_state(self) -> SafetyState:
        return self._safety_state

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
            )

        self._safety_state.record_success()
        prediction_errors = compute_prediction_errors(
            self._graph, current=frame.activations, previous=self._previous_frame
        )

        frozen = self._safety_state.frozen
        if not frozen:
            for edge in self._graph.edges:
                # Must match CognitiveGraph.activate()'s own source_value()
                # routing exactly: a delay=0 edge's contribution this tick
                # came from sense_inputs (this tick), never previous_frame
                # -- using previous_frame here for every edge regardless of
                # delay_ticks would learn from a value the graph never
                # actually used to compute target_current.
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
                        source_id=source_id, target_id=target_id, source_active=True, target_active=True, tick=tick
                    )

        structural_mutations_applied = 0
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and tick % interval == 0:
            proposed = self._structural_plasticity.propose(self._graph, kernel_limits=self._kernel_limits, tick=tick)
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
                self._graph = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                structural_mutations_applied = len(all_mutations)
            self._structural_plasticity.reconcile({node.node_id for node in self._graph.nodes})

        self._previous_frame = dict(frame.activations)
        return CognitiveBridgeResult(
            tick=tick,
            activations=frame.activations,
            readouts=frame.readouts,
            prediction_errors=prediction_errors,
            structural_mutations_applied=structural_mutations_applied,
            frozen=frozen,
        )
