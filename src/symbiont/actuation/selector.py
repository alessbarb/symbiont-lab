from __future__ import annotations

import math
from collections.abc import Mapping

from .types import MotorIntent


class MotorIntentSelector:
    """Deterministic cognitive-readout -> MotorIntent selection (spec §9)."""

    def __init__(self, *, selection_threshold: float = 0.1) -> None:
        if (
            isinstance(selection_threshold, bool)
            or not isinstance(selection_threshold, (int, float))
            or not math.isfinite(float(selection_threshold))
            or not 0.0 <= float(selection_threshold) <= 1.0
        ):
            raise ValueError("selection_threshold must be within [0, 1]")
        self.selection_threshold = float(selection_threshold)

    def select(self, motor_readouts: Mapping[str, float]) -> MotorIntent | None:
        candidates: list[tuple[float, str]] = []
        for actuator_id, raw in motor_readouts.items():
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            value = float(raw)
            if not math.isfinite(value):
                continue
            activation = max(0.0, min(1.0, value))
            if activation >= self.selection_threshold:
                candidates.append((activation, str(actuator_id)))
        if not candidates:
            return None
        # Highest activation wins; lexical actuator_id is the deterministic
        # tie-breaker. No laboratory/world RNG participates.
        activation, actuator_id = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
        return MotorIntent(actuator_id=actuator_id, activation=activation)
