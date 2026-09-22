"""Endogenous bounded metaplastic phenotype regulation.

This module belongs to the research subject. It has no World/Lab imports and
receives only internal prediction dynamics and inferred disruption state.

Preregistered design:
docs/design/endogenous-metaplastic-epigenetics-v1.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

from ..lineage.germline import LocusSpec


@dataclass(slots=True)
class PhenotypicRegulationState:
    """Lifetime regulation of supported cognitive expression.

    The state is deliberately generic and non-semantic. It does not know why
    prediction error changed, what a signal means, whether the organism is
    surviving, or whether an evaluator considers an outcome successful.
    """

    birth_expression: dict[str, float]
    specs: Mapping[str, LocusSpec]
    current_expression: dict[str, float] = field(default_factory=dict)
    prediction_error_ema: float = 0.0
    error_initialized: bool = False
    stable_shift_ticks: dict[str, int] = field(default_factory=dict)
    min_capture_delta: float = 0.02
    persistence_ticks_required: int = 64
    error_ema_alpha: float = 0.05
    expression_adaptation_rate: float = 0.08

    SUPPORTED_LOCI = ("learning_rate", "exploration_rate")

    def __post_init__(self) -> None:
        if self.persistence_ticks_required < 1:
            raise ValueError("persistence_ticks_required must be >= 1")
        if not 0.0 < self.error_ema_alpha <= 1.0:
            raise ValueError("error_ema_alpha must be in (0, 1]")
        if not 0.0 < self.expression_adaptation_rate <= 1.0:
            raise ValueError("expression_adaptation_rate must be in (0, 1]")

        if not self.current_expression:
            self.current_expression = {
                locus: float(self.birth_expression[locus])
                for locus in self.SUPPORTED_LOCI
                if locus in self.birth_expression
            }
        for locus in self.current_expression:
            self.stable_shift_ticks.setdefault(locus, 0)

    def _bounded(self, locus: str, value: float) -> float:
        spec = self.specs.get(locus)
        if spec is None:
            return float(value)
        return float(spec.clamp(value))

    def _target_expression(
        self,
        *,
        locus: str,
        prediction_pressure: float,
        disruption: bool,
    ) -> float:
        birth = float(self.birth_expression[locus])
        spec = self.specs.get(locus)
        if spec is None:
            return birth
        span = float(spec.maximum) - float(spec.minimum)

        if locus == "learning_rate":
            # Persistent model mismatch raises plasticity within constitution.
            offset = span * 0.05 * prediction_pressure
        elif locus == "exploration_rate":
            # Exploration responds to model mismatch plus internally inferred
            # disruption. Neither term includes external semantics or reward.
            offset = span * (
                0.08 * prediction_pressure + (0.04 if disruption else 0.0)
            )
        else:
            offset = 0.0
        return self._bounded(locus, birth + offset)

    def update(
        self,
        *,
        prediction_error: float,
        disruption: bool,
    ) -> tuple[dict[str, float], tuple[str, ...]]:
        """Update expression and return loci eligible for germline capture."""
        if not math.isfinite(prediction_error):
            prediction_error = 0.0
        bounded_error = max(0.0, min(1.0, abs(float(prediction_error))))

        if not self.error_initialized:
            self.prediction_error_ema = bounded_error
            self.error_initialized = True
        else:
            self.prediction_error_ema = (
                (1.0 - self.error_ema_alpha) * self.prediction_error_ema
                + self.error_ema_alpha * bounded_error
            )

        # Absolute internally observed model mismatch provides sustained
        # pressure; no evaluator-defined success or fitness enters here.
        pressure = max(0.0, min(1.0, self.prediction_error_ema))

        eligible: list[str] = []
        for locus in self.SUPPORTED_LOCI:
            if locus not in self.current_expression or locus not in self.birth_expression:
                continue

            current = float(self.current_expression[locus])
            target = self._target_expression(
                locus=locus,
                prediction_pressure=pressure,
                disruption=disruption,
            )
            updated = current + self.expression_adaptation_rate * (target - current)
            updated = self._bounded(locus, updated)
            self.current_expression[locus] = updated

            shift = abs(updated - float(self.birth_expression[locus]))
            if shift >= self.min_capture_delta:
                self.stable_shift_ticks[locus] = self.stable_shift_ticks.get(locus, 0) + 1
            else:
                self.stable_shift_ticks[locus] = 0

            if self.stable_shift_ticks[locus] >= self.persistence_ticks_required:
                eligible.append(locus)

        return dict(self.current_expression), tuple(sorted(eligible))


__all__ = ["PhenotypicRegulationState"]
