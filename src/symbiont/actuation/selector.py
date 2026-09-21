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

    def select_many(
        self,
        motor_readouts: Mapping[str, float],
        *,
        max_concurrent: int | None = None,
    ) -> tuple[MotorIntent, ...]:
        if max_concurrent is not None and (
            isinstance(max_concurrent, bool)
            or not isinstance(max_concurrent, int)
            or max_concurrent < 1
        ):
            raise ValueError("max_concurrent must be a positive int or None")
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
        ordered = sorted(candidates, key=lambda item: (-item[0], item[1]))
        selected = ordered if max_concurrent is None else ordered[:max_concurrent]
        return tuple(
            MotorIntent(actuator_id=actuator_id, activation=activation)
            for activation, actuator_id in selected
        )

    def select(self, motor_readouts: Mapping[str, float]) -> MotorIntent | None:
        """Compatibility view: strongest currently selectable intent."""
        intents = self.select_many(motor_readouts, max_concurrent=1)
        return intents[0] if intents else None
