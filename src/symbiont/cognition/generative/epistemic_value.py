"""Epistemic value signals for agency-side comparison, never action authority."""

from __future__ import annotations

from collections.abc import Iterable
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

    @staticmethod
    def pairwise_discrimination(predictions: Iterable[tuple[str, ...]]) -> float:
        """Estimate how often two internal forecasts imply different outcomes.

        This is a comparison signal over organism-owned hypotheses only.  It
        does not inspect reality, score actions, or select an observation.
        With fewer than two forecasts there is no disagreement to resolve.
        """
        normalized = tuple(tuple(item) for item in predictions)
        if len(normalized) < 2:
            return 0.0
        pairs = len(normalized) * (len(normalized) - 1) // 2
        differing = sum(
            left != right
            for index, left in enumerate(normalized)
            for right in normalized[index + 1 :]
        )
        return differing / pairs


__all__ = ["EpistemicValue", "EpistemicValueEstimator"]
