from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Mapping

from ...cognition.graph import CognitiveGraph
from ...cognition.learning import PredictionError, ShadowPrediction, huber_loss
from ...cognition.structure import Mutation
from ...cognition.types import EdgeKind, NodeKind

_MAX_SHADOW_PREDICTIONS = 16384
_MAX_LIVE_SHADOW_FACTOR = 8
_MAX_PRELIMINARY_SHADOW_FACTOR = 16
_ACTIVITY_THRESHOLD = 0.1


@dataclass(slots=True)
class PredictorUtility:
    """Bounded evidence that a materialized predictor beats persistence."""

    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0
    recent_gain: float = 0.0
    negative_streak: int = 0
    positive_streak: int = 0

    def observe(self, *, model_loss: float, persistence_loss: float) -> None:
        if not math.isfinite(model_loss) or not math.isfinite(persistence_loss):
            return
        model = max(0.0, float(model_loss))
        persistence = max(0.0, float(persistence_loss))
        sample_gain = persistence - model
        self.samples += 1
        self.model_loss += model
        self.persistence_loss += persistence
        alpha = 0.125
        self.recent_gain = (
            sample_gain
            if self.samples == 1
            else (1.0 - alpha) * self.recent_gain + alpha * sample_gain
        )
        epsilon = 1e-4
        if self.recent_gain < -epsilon:
            self.negative_streak += 1
            self.positive_streak = 0
        elif self.recent_gain > epsilon:
            self.positive_streak += 1
            self.negative_streak = 0
        else:
            self.negative_streak = max(0, self.negative_streak - 1)
            self.positive_streak = max(0, self.positive_streak - 1)

    @property
    def predictive_gain(self) -> float:
        if self.samples <= 0:
            return 0.0
        return (self.persistence_loss - self.model_loss) / self.samples

    def checkpoint(self, predictor_id: str) -> dict[str, object]:
        return {
            "predictor_id": predictor_id,
            "samples": self.samples,
            "model_loss": self.model_loss,
            "persistence_loss": self.persistence_loss,
            "recent_gain": self.recent_gain,
            "negative_streak": self.negative_streak,
            "positive_streak": self.positive_streak,
        }


@dataclass(slots=True)
class PredictorRetirement:
    predictor_id: str
    entered_tick: int
    last_evaluated_tick: int

    def checkpoint(self) -> dict[str, object]:
        return {
            "predictor_id": self.predictor_id,
            "entered_tick": self.entered_tick,
            "last_evaluated_tick": self.last_evaluated_tick,
        }


class PredictorLifecycle:
    """Own predictor evidence, quarantine and shadow-hypothesis state."""

    def __init__(self) -> None:
        self.utility: dict[str, PredictorUtility] = {}
        self.retirement: dict[str, PredictorRetirement] = {}
        self.shadows: dict[tuple[str, str], ShadowPrediction] = {}
        self.preliminary_support: dict[tuple[str, str], int] = {}
        self._shadow_cache: tuple[ShadowPrediction, ...] | None = None
        self._shadow_prune_dirty = True
        self._shadow_prune_topology_revision = -1

    @property
    def shadow_predictions(self) -> tuple[ShadowPrediction, ...]:
        if self._shadow_cache is None:
            self._shadow_cache = tuple(
                sorted(
                    self.shadows.values(),
                    key=lambda item: (item.source_id, item.target_id),
                )
            )
        return self._shadow_cache

    def invalidate_shadow_cache(self) -> None:
        self._shadow_cache = None

    def mark_shadow_dirty(self) -> None:
        self._shadow_prune_dirty = True

    @staticmethod
    def live_shadow_limit(max_nodes: int) -> int:
        return min(
            _MAX_SHADOW_PREDICTIONS,
            max(32, max_nodes * _MAX_LIVE_SHADOW_FACTOR),
        )

    @staticmethod
    def preliminary_shadow_limit(max_nodes: int) -> int:
        return min(
            _MAX_SHADOW_PREDICTIONS,
            max(64, max_nodes * _MAX_PRELIMINARY_SHADOW_FACTOR),
        )

    def record_prediction_errors(
        self,
        errors: tuple[PredictionError, ...],
        *,
        previous: Mapping[str, float],
        current: Mapping[str, float],
    ) -> None:
        for error in errors:
            target_previous = previous.get(error.target_id)
            target_current = current.get(error.target_id)
            if target_previous is None or target_current is None:
                continue
            utility = self.utility.setdefault(
                error.predictor_id,
                PredictorUtility(),
            )
            utility.observe(
                model_loss=error.loss,
                persistence_loss=huber_loss(target_current - target_previous),
            )

    def update_retirement(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        soft_node_limit: int,
        structural_wait: int,
        minimum_support: int,
        tentative_lifetime_ticks: int,
    ) -> None:
        predictor_ids = {
            node.node_id
            for node in graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        capacity_pressure = len(graph.nodes) >= soft_node_limit
        minimum_samples = max(8, minimum_support)
        enter_streak = max(4, minimum_support // 2)
        leave_streak = max(4, minimum_support // 2)
        wait_grace = max(1, tentative_lifetime_ticks)
        aged_structural_demand = structural_wait >= wait_grace

        if not capacity_pressure:
            self.retirement.clear()
            return

        for predictor_id in tuple(self.retirement):
            if predictor_id not in predictor_ids:
                self.retirement.pop(predictor_id, None)

        if self.retirement:
            predictor_id = next(iter(sorted(self.retirement)))
            utility = self.utility.get(predictor_id)
            retirement = self.retirement[predictor_id]
            retirement.last_evaluated_tick = tick
            if (
                utility is not None
                and utility.recent_gain > 0.0
                and utility.positive_streak >= leave_streak
            ):
                self.retirement.pop(predictor_id, None)
            else:
                return

        candidates: list[tuple[float, float, int, str]] = []
        for predictor_id in sorted(predictor_ids):
            utility = self.utility.get(predictor_id)
            if utility is None or utility.samples < minimum_samples:
                continue
            required_negative_streak = 1 if aged_structural_demand else enter_streak
            if utility.recent_gain >= -1e-4:
                continue
            if utility.negative_streak < required_negative_streak:
                continue
            if utility.predictive_gain > 0.0 and not aged_structural_demand:
                continue
            candidates.append(
                (
                    utility.recent_gain,
                    utility.predictive_gain,
                    -utility.negative_streak,
                    predictor_id,
                )
            )
        if candidates:
            _, _, _, predictor_id = min(candidates)
            self.retirement[predictor_id] = PredictorRetirement(
                predictor_id=predictor_id,
                entered_tick=tick,
                last_evaluated_tick=tick,
            )

    def propose_promotion(
        self,
        source_id: str,
        target_id: str,
        *,
        graph: CognitiveGraph,
        develop_senses: bool,
    ) -> tuple[str, tuple[Mutation, ...]] | None:
        shadow = self.shadows.get((source_id, target_id))
        if shadow is None or not shadow.promotable or not develop_senses:
            return None
        source_node = graph.node_by_id(source_id)
        if source_node is None or source_node.kind is not NodeKind.SENSE:
            return None
        if graph.node_by_id(target_id) is None or target_id in self.retirement:
            return None
        if any(
            node.kind is NodeKind.PREDICTOR
            and node.predicts_node_id == target_id
            for node in graph.nodes
        ):
            return None

        candidate_id = f"predictor:{source_id}:{target_id}"
        digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]
        predictor_id = f"predictor_{digest}"
        if graph.node_by_id(predictor_id) is not None:
            return None

        return (
            candidate_id,
            (
                Mutation(
                    kind="add_node",
                    payload={
                        "node_id": predictor_id,
                        "kind": NodeKind.PREDICTOR,
                        "predicts_node_id": target_id,
                    },
                ),
                Mutation(
                    kind="add_edge",
                    payload={
                        "source_id": source_id,
                        "target_id": predictor_id,
                        "kind": EdgeKind.PREDICTIVE,
                        "weight": 1.0,
                        "plasticity": 0.25,
                        "delay_ticks": 0,
                    },
                ),
            ),
        )

    def nominate_shadow(
        self,
        *,
        tiebreak,
    ) -> tuple[str, str] | None:
        ranked = sorted(
            (
                candidate
                for candidate in self.shadows.values()
                if candidate.promotable
            ),
            key=lambda candidate: (
                -candidate.predictive_gain,
                -candidate.samples,
                tiebreak(
                    f"{candidate.source_id}:{candidate.target_id}"
                ),
                candidate.source_id,
                candidate.target_id,
            ),
        )
        if not ranked:
            return None
        candidate = ranked[0]
        return candidate.source_id, candidate.target_id

    def observe_shadows(
        self,
        *,
        previous_frame: Mapping[str, float],
        activations: Mapping[str, float],
        node_kinds: Mapping[str, NodeKind],
        topology_revision: int,
        max_nodes: int,
    ) -> None:
        """Update bounded lag-1 shadow hypotheses from one cognitive frame."""
        preliminary_min = 1
        live_limit = self.live_shadow_limit(max_nodes)
        if len(self.shadows) >= live_limit:
            self.prune_shadows(
                node_kinds=node_kinds,
                topology_revision=topology_revision,
                max_nodes=max_nodes,
            )

        for source_id, source_value in previous_frame.items():
            if node_kinds.get(source_id) is not NodeKind.SENSE:
                continue
            for target_id, target_value in activations.items():
                if source_id == target_id or target_id not in previous_frame:
                    continue
                target_previous = previous_frame[target_id]
                key = (source_id, target_id)
                predictor = self.shadows.get(key)
                if predictor is not None:
                    previous_status = predictor.status
                    predictor.observe(
                        source_value,
                        target_value,
                        target_previous,
                    )
                    if (
                        previous_status != "retired"
                        and predictor.status == "retired"
                    ):
                        self.mark_shadow_dirty()
                    continue

                if abs(source_value) < _ACTIVITY_THRESHOLD:
                    continue
                support = self.preliminary_support.get(key, 0) + 1
                self.preliminary_support[key] = support
                if support < preliminary_min:
                    continue
                if len(self.shadows) >= live_limit:
                    continue
                predictor = ShadowPrediction(source_id, target_id)
                self.shadows[key] = predictor
                self.invalidate_shadow_cache()
                self.preliminary_support.pop(key, None)
                predictor.observe(
                    source_value,
                    target_value,
                    target_previous,
                )

        self.prune_preliminary(
            node_kinds=node_kinds,
            max_nodes=max_nodes,
        )
        self.prune_shadows(
            node_kinds=node_kinds,
            topology_revision=topology_revision,
            max_nodes=max_nodes,
        )

    def prune_preliminary(
        self,
        *,
        node_kinds: Mapping[str, NodeKind],
        max_nodes: int,
    ) -> None:
        live_ids = set(node_kinds)
        self.preliminary_support = {
            key: support
            for key, support in self.preliminary_support.items()
            if node_kinds.get(key[0]) is NodeKind.SENSE and key[1] in live_ids
        }
        limit = self.preliminary_shadow_limit(max_nodes)
        if len(self.preliminary_support) <= limit:
            return
        retained = sorted(
            self.preliminary_support.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
        self.preliminary_support = dict(retained)

    def prune_shadows(
        self,
        *,
        node_kinds: Mapping[str, NodeKind],
        topology_revision: int,
        max_nodes: int,
    ) -> None:
        topology_changed = (
            self._shadow_prune_topology_revision != topology_revision
        )
        limit = self.live_shadow_limit(max_nodes)
        over_limit = len(self.shadows) > limit
        if not self._shadow_prune_dirty and not topology_changed and not over_limit:
            return

        live_ids = set(node_kinds)
        retained_predictions = {
            key: candidate
            for key, candidate in self.shadows.items()
            if (
                candidate.status != "retired"
                and node_kinds.get(candidate.source_id) is NodeKind.SENSE
                and candidate.target_id in live_ids
            )
        }
        if len(retained_predictions) != len(self.shadows):
            self.shadows = retained_predictions
            self.invalidate_shadow_cache()
        if len(self.shadows) > limit:
            ranked = sorted(
                self.shadows.items(),
                key=lambda item: (
                    item[1].status != "supported",
                    -item[1].predictive_gain,
                    -item[1].samples,
                    item[0],
                ),
            )
            self.shadows = dict(ranked[:limit])
            self.invalidate_shadow_cache()

        self._shadow_prune_dirty = False
        self._shadow_prune_topology_revision = topology_revision
