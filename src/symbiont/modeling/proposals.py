from __future__ import annotations

from dataclasses import dataclass
import math


_MAX_TOKEN = 96
_MAX_MODEL_ID = 128


def _token(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_TOKEN:
        raise ValueError(f"{name} must be a bounded non-empty token")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValueError(f"{name} must contain printable non-whitespace ASCII only")
    return value


def _model_id(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_MODEL_ID:
        raise ValueError("model_id must be a bounded non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class ModelPredictionProposal:
    """A model suggestion that remains epistemically a prediction, never evidence."""

    target_token: str
    horizon_class: int
    predicted_token: str
    confidence_class: int
    model_id: str

    def __post_init__(self) -> None:
        _token(self.target_token, "target_token")
        _token(self.predicted_token, "predicted_token")
        _model_id(self.model_id)
        if isinstance(self.horizon_class, bool) or not isinstance(self.horizon_class, int) or not 1 <= self.horizon_class <= 16:
            raise ValueError("horizon_class must be within [1, 16]")
        if isinstance(self.confidence_class, bool) or not isinstance(self.confidence_class, int) or not 0 <= self.confidence_class <= 7:
            raise ValueError("confidence_class must be within [0, 7]")


@dataclass(frozen=True, slots=True)
class ModelHypothesisProposal:
    """A closed relational proposal; it cannot directly alter factual memory."""

    subject_token: str
    relation_token: str
    object_token: str
    confidence_class: int
    model_id: str

    def __post_init__(self) -> None:
        _token(self.subject_token, "subject_token")
        _token(self.relation_token, "relation_token")
        _token(self.object_token, "object_token")
        _model_id(self.model_id)
        if isinstance(self.confidence_class, bool) or not isinstance(self.confidence_class, int) or not 0 <= self.confidence_class <= 7:
            raise ValueError("confidence_class must be within [0, 7]")


def confidence_class(probability: float) -> int:
    if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(float(probability)):
        raise ValueError("probability must be finite")
    value = max(0.0, min(1.0, float(probability)))
    return min(7, int(value * 8.0))
