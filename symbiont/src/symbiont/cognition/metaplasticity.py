from __future__ import annotations

import math
from dataclasses import dataclass, fields

_LOWER_IS_BETTER = ("prediction_error", "representation_cost", "instability")
_HIGHER_IS_BETTER = ("information_retained", "calibration")


@dataclass(slots=True, frozen=True)
class LearningObjective:
    prediction_error: float
    representation_cost: float
    instability: float
    information_retained: float
    calibration: float

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not math.isfinite(value):
                raise ValueError(f"{field.name} must be finite, got {value!r}")


def dominates(a: LearningObjective, b: LearningObjective) -> bool:
    at_least_as_good = True
    strictly_better_somewhere = False
    for field in _LOWER_IS_BETTER:
        a_value, b_value = getattr(a, field), getattr(b, field)
        if a_value > b_value:
            at_least_as_good = False
        elif a_value < b_value:
            strictly_better_somewhere = True
    for field in _HIGHER_IS_BETTER:
        a_value, b_value = getattr(a, field), getattr(b, field)
        if a_value < b_value:
            at_least_as_good = False
        elif a_value > b_value:
            strictly_better_somewhere = True
    return at_least_as_good and strictly_better_somewhere


@dataclass(slots=True)
class MetaParameter:
    value: float
    minimum: float
    maximum: float
    max_step: float

    def propose(
        self,
        *,
        candidate_delta: float,
        previous_window_objective: LearningObjective,
        current_window_objective: LearningObjective,
        frozen: bool = False,
    ) -> None:
        if frozen:
            return  # safe mode (SafetyState.frozen) -- no parameter drift while frozen
        if dominates(previous_window_objective, current_window_objective):
            return  # things got worse -- never commit
        clipped_delta = max(-self.max_step, min(self.max_step, candidate_delta))
        self.value = max(self.minimum, min(self.maximum, self.value + clipped_delta))


@dataclass(slots=True)
class SafetyState:
    consecutive_failures: int = 0
    frozen: bool = False

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.frozen = True

    def reset(self) -> None:
        self.consecutive_failures = 0
        self.frozen = False
