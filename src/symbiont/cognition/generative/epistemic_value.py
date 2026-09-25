"""Epistemic value signals for agency-side comparison, never action authority."""

from __future__ import annotations

from dataclasses import dataclass

from .types import bounded_identifier, unit_interval


@dataclass(frozen=True, slots=True)
class EpistemicValue:
    candidate_ref: str
    expected_uncertainty_reduction: float
    expected_hypothesis_discrimination: float
    model_disagreement: float

    def __post_init__(self) -> None:
        bounded_identifier(self.candidate_ref, name="candidate_ref")
        unit_interval(
            self.expected_uncertainty_reduction,
            name="expected_uncertainty_reduction",
        )
        unit_interval(
            self.expected_hypothesis_discrimination,
            name="expected_hypothesis_discrimination",
        )
        unit_interval(self.model_disagreement, name="model_disagreement")

    @property
    def comparison_score(self) -> float:
        """Return a bounded comparison signal, not a reward or action command."""

        return (
            self.expected_uncertainty_reduction
            + self.expected_hypothesis_discrimination
            + self.model_disagreement
        ) / 3.0


class EpistemicValueEstimator:
    """Derive comparison-only epistemic value from generated expectations."""

    @staticmethod
    def estimate(
        *,
        candidate_ref: str,
        current_uncertainty: float,
        expected_uncertainty: float,
        expected_hypothesis_discrimination: float,
        model_disagreement: float,
    ) -> EpistemicValue:
        unit_interval(current_uncertainty, name="current_uncertainty")
        unit_interval(expected_uncertainty, name="expected_uncertainty")
        reduction = max(0.0, current_uncertainty - expected_uncertainty)
        return EpistemicValue(
            candidate_ref=candidate_ref,
            expected_uncertainty_reduction=reduction,
            expected_hypothesis_discrimination=expected_hypothesis_discrimination,
            model_disagreement=model_disagreement,
        )


__all__ = ["EpistemicValue", "EpistemicValueEstimator"]
