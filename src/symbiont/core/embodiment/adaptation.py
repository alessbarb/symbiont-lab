"""Evidence-driven embodiment adaptation; never a fixed adaptation timer."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from .dynamics import PredictionResidual


@dataclass(frozen=True, slots=True)
class AdaptationSnapshot:
    prediction_error_recent: float
    prediction_error_baseline: float
    prediction_shock: float
    schema_uncertainty: float
    causal_confidence: float
    controllability_confidence: float
    competence_revalidation_ratio: float
    disruption_score: float
    adaptation_ticks: int
    first_shock_tick: int | None
    first_revision_tick: int | None
    recovery_tick: int | None

    @property
    def converged(self) -> bool:
        if self.adaptation_ticks < 8:
            return False
        return (
            self.prediction_shock <= 0.20
            and self.schema_uncertainty <= 0.35
            and self.causal_confidence >= 0.45
            and self.controllability_confidence >= 0.35
        )


class EmbodimentAdaptation:
    """Track evidence of adaptation without declaring a hard-coded phase."""

    SCHEMA_VERSION = 1

    def __init__(self) -> None:
        self.prediction_error_recent = 0.0
        self.prediction_error_baseline = 0.0
        self.prediction_shock = 0.0
        self.schema_uncertainty = 1.0
        self.causal_confidence = 0.0
        self.controllability_confidence = 0.0
        self.competence_revalidation_ratio = 0.0
        self.disruption_score = 0.0
        self.adaptation_ticks = 0
        self.first_shock_tick: int | None = None
        self.first_revision_tick: int | None = None
        self.recovery_tick: int | None = None
        self._stable_ticks = 0

    def observe(
        self,
        *,
        tick: int,
        residuals: Iterable[PredictionResidual] = (),
        schema_confidence: float | None = None,
        causal_confidence: float | None = None,
        controllability_confidence: float | None = None,
        revalidated_competences: int = 0,
        candidate_competences: int = 0,
        schema_revised: bool = False,
    ) -> AdaptationSnapshot:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        self.adaptation_ticks += 1
        errors = [max(0.0, float(item.error)) for item in residuals]
        current = sum(errors) / len(errors) if errors else self.prediction_error_recent
        if self.adaptation_ticks == 1:
            self.prediction_error_recent = current
            self.prediction_error_baseline = current
        else:
            self.prediction_error_recent += 0.20 * (current - self.prediction_error_recent)
            # Baseline follows slowly so abrupt mismatch remains observable.
            self.prediction_error_baseline += 0.015 * (
                current - self.prediction_error_baseline
            )
        denom = max(0.05, self.prediction_error_baseline)
        self.prediction_shock = max(
            0.0,
            min(1.0, (self.prediction_error_recent - self.prediction_error_baseline) / denom),
        )
        if self.prediction_shock >= 0.5 and self.first_shock_tick is None:
            self.first_shock_tick = tick

        if schema_confidence is not None:
            bounded = max(0.0, min(1.0, float(schema_confidence)))
            self.schema_uncertainty = 1.0 - bounded
        if causal_confidence is not None:
            self.causal_confidence = max(0.0, min(1.0, float(causal_confidence)))
        if controllability_confidence is not None:
            self.controllability_confidence = max(
                0.0, min(1.0, float(controllability_confidence))
            )
        if candidate_competences > 0:
            self.competence_revalidation_ratio = max(
                0.0,
                min(1.0, revalidated_competences / candidate_competences),
            )
        else:
            self.competence_revalidation_ratio = 0.0

        if schema_revised and self.first_revision_tick is None:
            self.first_revision_tick = tick

        self.disruption_score = max(
            self.prediction_shock,
            self.schema_uncertainty * (1.0 - self.causal_confidence),
            1.0 - self.controllability_confidence,
        )
        snap = self.snapshot()
        if snap.converged:
            self._stable_ticks += 1
            if self._stable_ticks >= 8 and self.recovery_tick is None:
                self.recovery_tick = tick
        else:
            self._stable_ticks = 0
            # A new disturbance after recovery re-opens adaptation.
            if self.prediction_shock >= 0.5:
                self.recovery_tick = None
        return self.snapshot()

    def snapshot(self) -> AdaptationSnapshot:
        return AdaptationSnapshot(
            prediction_error_recent=self.prediction_error_recent,
            prediction_error_baseline=self.prediction_error_baseline,
            prediction_shock=self.prediction_shock,
            schema_uncertainty=self.schema_uncertainty,
            causal_confidence=self.causal_confidence,
            controllability_confidence=self.controllability_confidence,
            competence_revalidation_ratio=self.competence_revalidation_ratio,
            disruption_score=self.disruption_score,
            adaptation_ticks=self.adaptation_ticks,
            first_shock_tick=self.first_shock_tick,
            first_revision_tick=self.first_revision_tick,
            recovery_tick=self.recovery_tick,
        )

    def checkpoint(self) -> dict[str, object]:
        snap = self.snapshot()
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{name: getattr(snap, name) for name in snap.__dataclass_fields__},
            "stable_ticks": self._stable_ticks,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "EmbodimentAdaptation":
        obj = cls()
        if payload is None:
            return obj
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported embodiment adaptation checkpoint")
        for name in (
            "prediction_error_recent",
            "prediction_error_baseline",
            "prediction_shock",
            "schema_uncertainty",
            "causal_confidence",
            "controllability_confidence",
            "competence_revalidation_ratio",
            "disruption_score",
        ):
            value = float(payload.get(name, getattr(obj, name)))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"invalid adaptation field {name}")
            setattr(obj, name, value)
        obj.adaptation_ticks = int(payload.get("adaptation_ticks", 0))
        obj.first_shock_tick = (
            int(payload["first_shock_tick"])
            if payload.get("first_shock_tick") is not None
            else None
        )
        obj.first_revision_tick = (
            int(payload["first_revision_tick"])
            if payload.get("first_revision_tick") is not None
            else None
        )
        obj.recovery_tick = (
            int(payload["recovery_tick"])
            if payload.get("recovery_tick") is not None
            else None
        )
        obj._stable_ticks = int(payload.get("stable_ticks", 0))
        return obj


__all__ = ["AdaptationSnapshot", "EmbodimentAdaptation"]
