"""Memory consolidation domain."""

from __future__ import annotations

from dataclasses import dataclass

from ..cognition.consolidation import (
    ConsolidationSignal,
    MemoryConsolidator,
    MemoryKind,
    novelty_from_drift_kind,
    surprise_from_loss,
)
from ..cognition.host_self_model import SelfModel
from .cognition import CognitionStepResult
from .context import TickContext
from .perception import PerceptionStepResult


@dataclass(frozen=True, slots=True)
class MemoryServices:
    consolidator: MemoryConsolidator
    self_model: SelfModel


class MemoryDomain:
    """Consolidate organism-owned experience without selecting actions."""

    def observe(
        self,
        *,
        services: MemoryServices,
        context: TickContext,
        perception: PerceptionStepResult,
        cognition: CognitionStepResult,
        reacclimation_remaining: int,
    ) -> None:
        if reacclimation_remaining > 0:
            return

        attended_capability_ids = {allocation.name for allocation in perception.allocations}
        capability_by_percept_name = {
            name: capability_id for capability_id, name in perception.percept_names.items()
        }
        prediction_loss_by_node: dict[str, float] = {}
        if cognition.cognition is not None:
            for error in cognition.cognition.prediction_errors:
                prediction_loss_by_node[error.target_id] = error.loss

        for percept_name, observation in perception.drift_observations.items():
            capability_id = capability_by_percept_name.get(percept_name)
            novelty = novelty_from_drift_kind(observation.kind)
            surprise = surprise_from_loss(prediction_loss_by_node.get(percept_name))
            attention = 1.0 if capability_id in attended_capability_ids else 0.0
            availability = (
                perception.availability_by_capability.get(
                    capability_id,
                    1.0,
                )
                if capability_id
                else 1.0
            )
            health = (
                services.self_model.health(
                    capability_id,
                    current_tick=max(0, context.symbiont_tick - 1),
                )
                if capability_id is not None
                else 0.5
            )
            reliability = max(
                0.0,
                min(1.0, availability * health),
            )
            services.consolidator.observe(
                percept_name,
                MemoryKind.SALIENT_EVENT,
                ConsolidationSignal(
                    novelty=novelty,
                    surprise=surprise,
                    attention=attention,
                    reliability=reliability,
                    coherence=0.0,
                ),
                tick=context.symbiont_tick,
            )

    @staticmethod
    def retained_units(
        *,
        drift_baseline_count: int,
        cognitive_node_count: int,
    ) -> float:
        return (
            max(0, int(drift_baseline_count)) * 0.001 + max(0, int(cognitive_node_count)) * 0.0005
        )
