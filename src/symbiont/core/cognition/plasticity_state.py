from __future__ import annotations

from ...cognition.checkpoint import quantize_weight
from ...cognition.graph import CognitiveGraph
from ..foundation.weight_stability import EdgeKey, WeightStabilityTracker


class PlasticityEngine:
    """Own durable weight-stability bookkeeping for CognitiveBridge.

    The bridge remains responsible for tick ordering and Oja eligibility. This
    component owns only the state that tracks which learned weights have become
    durable enough to export through checkpoints.
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
