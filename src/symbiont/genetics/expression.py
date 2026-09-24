"""Lifetime expression of Genome v2 predispositions.

Evidence observed through tick t may update this state only for tick t+1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

from .genome import AdaptiveGeneRange, Genome


def _unit(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True, slots=True)
class RegulatorySignals:
    uncertainty: float = 0.0
    novelty: float = 0.0
    prediction_error: float = 0.0
    controllability_loss: float = 0.0
    embodiment_mismatch: float = 0.0
    resource_pressure: float = 0.0

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite in [0,1]")


@dataclass(slots=True)
class GeneExpressionState:
    effective_learning_rate: float
    effective_structural_plasticity: float
    effective_growth_threshold: float
    effective_pruning_threshold: float
    exploration_drive: float
    regulatory_activation: dict[str, float] = field(default_factory=dict)
    update_count: int = 0

    @classmethod
    def from_genome(cls, genome: Genome) -> "GeneExpressionState":
        return cls(
            effective_learning_rate=genome.plasticity.learning_rate.baseline,
            effective_structural_plasticity=genome.plasticity.structural_plasticity.baseline,
            effective_growth_threshold=genome.structure.growth_threshold.baseline,
            effective_pruning_threshold=genome.structure.pruning_threshold.baseline,
            exploration_drive=genome.sensorimotor.spontaneous_activity_baseline,
            regulatory_activation={},
            update_count=0,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "effective_learning_rate": self.effective_learning_rate,
            "effective_structural_plasticity": self.effective_structural_plasticity,
            "effective_growth_threshold": self.effective_growth_threshold,
            "effective_pruning_threshold": self.effective_pruning_threshold,
            "exploration_drive": self.exploration_drive,
            "regulatory_activation": dict(self.regulatory_activation),
            "update_count": self.update_count,
        }


class ExpressionRegulator:
    """Single bounded metaplastic regulator for the canonical runtime."""

    @staticmethod
    def _move(current: float, target: float, spec: AdaptiveGeneRange, pressure: float) -> float:
        target = max(spec.minimum, min(spec.maximum, target))
        max_step = max(0.0, spec.adaptation_rate) * _unit(pressure)
        delta = max(-max_step, min(max_step, target - current))
        return max(spec.minimum, min(spec.maximum, current + delta))

    def update(
        self,
        genome: Genome,
        state: GeneExpressionState,
        signals: RegulatorySignals,
        *,
        frozen: bool = False,
    ) -> GeneExpressionState:
        if frozen:
            return GeneExpressionState(
                effective_learning_rate=state.effective_learning_rate,
                effective_structural_plasticity=state.effective_structural_plasticity,
                effective_growth_threshold=state.effective_growth_threshold,
                effective_pruning_threshold=state.effective_pruning_threshold,
                exploration_drive=state.exploration_drive,
                regulatory_activation=dict(state.regulatory_activation),
                update_count=state.update_count,
            )

        r = genome.regulation
        mismatch_pressure = _unit(
            r.uncertainty_gain * signals.uncertainty
            + r.novelty_gain * signals.novelty
            + r.prediction_error_gain * signals.prediction_error
            + r.controllability_loss_gain * signals.controllability_loss
            + r.embodiment_mismatch_gain * signals.embodiment_mismatch
        )
        resource_pressure = _unit(signals.resource_pressure)
        adaptive_pressure = max(mismatch_pressure, resource_pressure)

        learning = genome.plasticity.learning_rate
        learning_target = learning.baseline + (
            learning.maximum - learning.baseline
        ) * mismatch_pressure
        learning_value = self._move(
            state.effective_learning_rate,
            learning_target,
            learning,
            adaptive_pressure,
        )

        structural = genome.plasticity.structural_plasticity
        structural_target = structural.baseline + (
            structural.maximum - structural.baseline
        ) * mismatch_pressure
        structural_value = self._move(
            state.effective_structural_plasticity,
            structural_target,
            structural,
            adaptive_pressure,
        )

        growth = genome.structure.growth_threshold
        growth_target = growth.baseline - (
            growth.baseline - growth.minimum
        ) * mismatch_pressure
        growth_value = self._move(
            state.effective_growth_threshold,
            growth_target,
            growth,
            adaptive_pressure,
        )

        pruning = genome.structure.pruning_threshold
        pruning_target = pruning.baseline - (
            pruning.baseline - pruning.minimum
        ) * mismatch_pressure
        pruning_value = self._move(
            state.effective_pruning_threshold,
            pruning_target,
            pruning,
            adaptive_pressure,
        )

        sm = genome.sensorimotor
        exploration_target = _unit(
            sm.spontaneous_activity_baseline
            + sm.uncertainty_exploration_gain * signals.uncertainty
            + sm.prediction_error_exploration_gain * signals.prediction_error
            + sm.reacclimation_sensitivity * signals.embodiment_mismatch
        )
        habituation = sm.exploration_habituation * (
            1.0
            - max(
                signals.uncertainty,
                signals.prediction_error,
                signals.embodiment_mismatch,
            )
        )
        exploration_target = _unit(exploration_target - habituation)

        alpha = _unit(r.regulation_smoothing)
        decay = _unit(r.regulation_decay)
        exploration_value = _unit(
            state.exploration_drive
            + alpha * (exploration_target - state.exploration_drive)
            + decay
            * (
                sm.spontaneous_activity_baseline
                - state.exploration_drive
            )
        )

        return GeneExpressionState(
            effective_learning_rate=learning_value,
            effective_structural_plasticity=structural_value,
            effective_growth_threshold=growth_value,
            effective_pruning_threshold=pruning_value,
            exploration_drive=exploration_value,
            regulatory_activation={
                "mismatch_pressure": mismatch_pressure,
                "resource_pressure": resource_pressure,
            },
            update_count=state.update_count + 1,
        )


def restore_expression_state(
    payload: Mapping[str, object],
    genome: Genome,
) -> GeneExpressionState:
    required = {
        "effective_learning_rate",
        "effective_structural_plasticity",
        "effective_growth_threshold",
        "effective_pruning_threshold",
        "exploration_drive",
        "regulatory_activation",
        "update_count",
    }
    if set(payload) != required:
        raise ValueError("expression checkpoint keys mismatch")

    def finite(name: str) -> float:
        value = payload[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"{name} must be finite numeric")
        return float(value)

    raw_activation = payload["regulatory_activation"]
    if not isinstance(raw_activation, Mapping):
        raise ValueError("regulatory_activation must be an object")
    activation: dict[str, float] = {}
    for key, value in raw_activation.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("regulatory activation values must be numeric")
        activation[str(key)] = _unit(float(value))

    count = payload["update_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("update_count must be a non-negative int")

    state = GeneExpressionState(
        effective_learning_rate=finite("effective_learning_rate"),
        effective_structural_plasticity=finite("effective_structural_plasticity"),
        effective_growth_threshold=finite("effective_growth_threshold"),
        effective_pruning_threshold=finite("effective_pruning_threshold"),
        exploration_drive=_unit(finite("exploration_drive")),
        regulatory_activation=activation,
        update_count=count,
    )
    checks = (
        (
            state.effective_learning_rate,
            genome.plasticity.learning_rate,
            "effective_learning_rate",
        ),
        (
            state.effective_structural_plasticity,
            genome.plasticity.structural_plasticity,
            "effective_structural_plasticity",
        ),
        (
            state.effective_growth_threshold,
            genome.structure.growth_threshold,
            "effective_growth_threshold",
        ),
        (
            state.effective_pruning_threshold,
            genome.structure.pruning_threshold,
            "effective_pruning_threshold",
        ),
    )
    for value, spec, name in checks:
        if not spec.minimum <= value <= spec.maximum:
            raise ValueError(f"{name} outside inherited range")
    return state


__all__ = [
    "ExpressionRegulator",
    "GeneExpressionState",
    "RegulatorySignals",
    "restore_expression_state",
]
