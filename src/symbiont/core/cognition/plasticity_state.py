from __future__ import annotations

from typing import Collection, Mapping

from ...cognition.checkpoint import quantize_weight
from ...cognition.graph import CognitiveGraph
from ...cognition.learning import apply_oja_update, update_eligibility
from ...cognition.structure import advance_edge_age
from ..foundation.weight_stability import EdgeKey, WeightStabilityTracker

_EDGE_USAGE_THRESHOLD = 1e-3
_ELIGIBILITY_THRESHOLD = 1e-6


class PlasticityEngine:
    """Own edge-local learning and durable weight-stability bookkeeping.

    CognitiveBridge owns tick ordering and decides which nodes participate in
    learning. This component owns eligibility updates, Oja weight updates,
    reversible retirement decay, edge ageing, and durable weight consolidation.
    """

    def __init__(self, *, kernel_limits) -> None:
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        self._tracked_edge_keys: set[tuple[str, str, str]] = set()

    def seed_new_edges(self, graph: CognitiveGraph) -> None:
        current_keys = {
            (edge.source_id, edge.target_id, edge.kind.value)
            for edge in graph.edges
        }
        self._weight_tracker.reconcile(current_keys)
        for edge in graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            if key in self._tracked_edge_keys:
                continue
            self._weight_tracker.seed(key, quantize_weight(edge.weight))
        self._tracked_edge_keys = current_keys

    @staticmethod
    def _decay_retiring_edge(
        edge,
        *,
        tick: int,
        retiring_predictors: Mapping[str, int],
        structural_wait: int,
        tentative_lifetime_ticks: int,
    ) -> None:
        retiring_id = None
        if edge.source_id in retiring_predictors:
            retiring_id = edge.source_id
        elif edge.target_id in retiring_predictors:
            retiring_id = edge.target_id
        if retiring_id is None:
            return
        age = max(0, tick - retiring_predictors[retiring_id])
        grace = tentative_lifetime_ticks // 4
        if age < grace:
            return
        wait_grace = max(1, tentative_lifetime_ticks)
        if structural_wait >= 2 * wait_grace:
            decay = 0.90
        elif structural_wait >= wait_grace:
            decay = 0.95
        else:
            decay = 0.99
        edge.weight *= decay
        if abs(edge.weight) < 1e-12:
            edge.weight = 0.0

    def apply_learning(
        self,
        graph: CognitiveGraph,
        *,
        sense_inputs: Mapping[str, float],
        previous_frame: Mapping[str, float],
        activations: Mapping[str, float],
        learning_nodes: Collection[str],
        retiring_predictors: Mapping[str, int],
        tick: int,
        eligibility_decay: float,
        learning_rate: float,
        tick_modulation: float,
        structural_plasticity_factor: float,
        tentative_lifetime_ticks: int,
        structural_wait: int,
        max_incoming_norm: float,
    ) -> None:
        learning_node_ids = set(learning_nodes)
        for edge in graph.edges:
            source_value = (
                sense_inputs.get(edge.source_id, 0.0)
                if edge.delay_ticks == 0
                else previous_frame.get(edge.source_id, 0.0)
            )
            target_current = activations.get(edge.target_id, 0.0)
            update_eligibility(
                edge,
                source_previous=source_value,
                target_current=target_current,
                decay=eligibility_decay,
            )
            retiring_edge = (
                edge.source_id in retiring_predictors
                or edge.target_id in retiring_predictors
            )
            eligible = (
                not retiring_edge
                and edge.source_id in learning_node_ids
                and edge.target_id in learning_node_ids
                and abs(edge.eligibility) >= _ELIGIBILITY_THRESHOLD
            )
            apply_oja_update(
                edge,
                source_activation=source_value,
                target_activation=target_current,
                learning_rate=learning_rate,
                modulation=(
                    tick_modulation
                    * edge.plasticity
                    * structural_plasticity_factor
                ),
                eligible=eligible,
                frozen=False,
            )
            if retiring_edge:
                self._decay_retiring_edge(
                    edge,
                    tick=tick,
                    retiring_predictors=retiring_predictors,
                    structural_wait=structural_wait,
                    tentative_lifetime_ticks=tentative_lifetime_ticks,
                )
            transmitted = edge.weight * source_value
            advance_edge_age(
                edge,
                tick=tick,
                used=abs(transmitted) >= _EDGE_USAGE_THRESHOLD,
            )

        self.observe_and_consolidate(
            graph,
            tick=tick,
            max_incoming_norm=max_incoming_norm,
        )

    def observe_and_consolidate(
        self,
        graph: CognitiveGraph,
        *,
        tick: int,
        max_incoming_norm: float,
    ) -> None:
        edges_by_target: dict[str, list] = {}
        for edge in graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            self._weight_tracker.observe(
                key,
                quantize_weight(edge.weight),
                tick=tick,
            )
            edges_by_target.setdefault(edge.target_id, []).append(edge)

        for target_edges in edges_by_target.values():
            keys: list[EdgeKey] = [
                (edge.source_id, edge.target_id, edge.kind.value)
                for edge in target_edges
            ]
            live_weights: dict[EdgeKey, float] = {
                key: float(edge.weight)
                for key, edge in zip(keys, target_edges)
            }
            self._weight_tracker.consolidate_node(
                keys,
                live_weights,
                max_incoming_norm=max_incoming_norm,
            )

    def weight_class_overrides(
        self,
        graph: CognitiveGraph,
    ) -> dict[tuple[str, str, str], int]:
        return {
            (edge.source_id, edge.target_id, edge.kind.value):
                self._weight_tracker.durable_class(
                    (edge.source_id, edge.target_id, edge.kind.value)
                )
            for edge in graph.edges
        }
