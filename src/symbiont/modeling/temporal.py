from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Generic, Protocol, TypeVar, runtime_checkable


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TemporalResourceUsage:
    """Comparable mechanism footprint without assigning cognitive value."""

    state_values: int
    learned_values: int
    observations: int
    updates: int

    def __post_init__(self) -> None:
        for name, value in (
            ("state_values", self.state_values),
            ("learned_values", self.learned_values),
            ("observations", self.observations),
            ("updates", self.updates),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class TemporalPrediction(Generic[T]):
    """A temporal hypothesis. It is never evidence by itself."""

    mechanism_id: str
    horizon: int
    value: T
    confidence: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.mechanism_id, str)
            or not self.mechanism_id
            or len(self.mechanism_id) > 128
        ):
            raise ValueError("mechanism_id must be a bounded non-empty string")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or self.horizon < 1:
            raise ValueError("horizon must be positive")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(float(self.confidence))
            or not 0.0 <= float(self.confidence) <= 1.0
        ):
            raise ValueError("confidence must be within [0, 1]")


@runtime_checkable
class TemporalMechanism(Protocol[T]):
    """Neutral experimental contract for private temporal mechanisms.

    Implementations may be symbolic, recurrent, reservoir-based or otherwise.
    The contract deliberately contains no semantic role such as motor, episodic,
    cultural or linguistic.
    """

    @property
    def mechanism_id(self) -> str: ...

    def observe(self, observation: T) -> None: ...

    def predict(self, *, horizon: int = 1) -> TemporalPrediction[T] | None: ...

    def resource_usage(self) -> TemporalResourceUsage: ...


__all__ = [
    "TemporalMechanism",
    "TemporalPrediction",
    "TemporalResourceUsage",
]
