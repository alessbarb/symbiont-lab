"""L8 Prospective Agency — core data transfer objects.

All types are immutable, slots-allocated, and contain no task-specific
semantics. The ``reason`` field of :class:`ProspectiveDecision` is closed to
technical values only; no behavioural or environmental labels appear here.
"""

from __future__ import annotations

from dataclasses import dataclass

_VALID_REASONS: frozenset[str] = frozenset(
    {
        "selected",
        "no_candidates",
        "no_active_model",
        "no_value_evidence",
        "insufficient_confidence",
        "insufficient_margin",
        "budget_exhausted",
        "physiology_dead",
    }
)


@dataclass(frozen=True, slots=True)
class ProspectiveCandidate:
    """One action the organism is considering prospectively.

    ``family`` is opaque; Sensorimotor v2 normally issues
    ``"competence"``. Agency must not interpret its value beyond routing to
    the matching predictor.
    """

    action_id: str
    family: str

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id:
            raise ValueError("action_id must be a non-empty string")
        if len(self.action_id) > 128:
            raise ValueError("action_id exceeds maximum length")
        if not isinstance(self.family, str) or not self.family:
            raise ValueError("family must be a non-empty string")
        if len(self.family) > 64:
            raise ValueError("family exceeds maximum length")


@dataclass(frozen=True, slots=True)
class CounterfactualPrediction:
    """A model-generated outcome prediction for one candidate action.

    This is a counterfactual: it describes what the model predicts *would*
    happen if the action were taken. It is never recorded as observed
    experience.
    """

    action_id: str
    predicted_outcome: str
    confidence_class: int

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id:
            raise ValueError("action_id must be a non-empty string")
        if not isinstance(self.predicted_outcome, str) or not self.predicted_outcome:
            raise ValueError("predicted_outcome must be a non-empty string")
        if len(self.predicted_outcome) > 96:
            raise ValueError("predicted_outcome token exceeds maximum length")
        if (
            isinstance(self.confidence_class, bool)
            or not isinstance(self.confidence_class, int)
            or not 0 <= self.confidence_class <= 7
        ):
            raise ValueError("confidence_class must be an integer in [0, 7]")


@dataclass(frozen=True, slots=True)
class OutcomeValueEstimate:
    """Statistical estimate of historical endogenous value for an outcome token.

    ``confidence`` is a normalised score in (0, 1] derived from ``samples``
    alone — never from environmental or evaluator-supplied metrics.
    """

    outcome_id: str
    samples: int
    mean_value: float
    variance: float
    confidence: float

    def __post_init__(self) -> None:
        import math

        if not isinstance(self.outcome_id, str) or not self.outcome_id:
            raise ValueError("outcome_id must be a non-empty string")
        if isinstance(self.samples, bool) or not isinstance(self.samples, int) or self.samples < 1:
            raise ValueError("samples must be a positive integer")
        for name, val in (
            ("mean_value", self.mean_value),
            ("variance", self.variance),
            ("confidence", self.confidence),
        ):
            if (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
            ):
                raise ValueError(f"{name} must be a finite float")
        if self.variance < 0.0:
            raise ValueError("variance must be non-negative")
        if not 0.0 < self.confidence <= 1.0:
            raise ValueError("confidence must be within (0, 1]")


@dataclass(frozen=True, slots=True)
class ProspectiveDecision:
    """The outcome of one deliberation cycle.

    Only ``selected`` decisions carry a non-None ``candidate_id``. All other
    fields are ``None`` when the decision did not select any action. The
    ``reason`` field is closed to the technical values in ``_VALID_REASONS``.
    """

    tick: int
    candidate_id: str | None
    predicted_outcome: str | None
    expected_value: float | None
    model_confidence: float | None
    value_confidence: float | None
    decision_margin: float | None
    reason: str

    def __post_init__(self) -> None:
        import math

        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if self.reason not in _VALID_REASONS:
            raise ValueError(
                f"reason {self.reason!r} is not a valid technical reason; "
                f"valid values: {sorted(_VALID_REASONS)}"
            )
        # Numeric optional fields must be finite when present
        for name, val in (
            ("expected_value", self.expected_value),
            ("model_confidence", self.model_confidence),
            ("value_confidence", self.value_confidence),
            ("decision_margin", self.decision_margin),
        ):
            if val is not None and (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
            ):
                raise ValueError(f"{name} must be a finite float or None")


__all__ = [
    "ProspectiveCandidate",
    "CounterfactualPrediction",
    "OutcomeValueEstimate",
    "ProspectiveDecision",
]
