"""Deterministic execution/observation/render cadence planning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionRates:
    """Four independent clocks with deterministic rational sampling."""

    physics_hz: int
    cognition_hz: int
    observation_hz: int
    render_hz: int

    @classmethod
    def resolve(
        cls,
        *,
        physics_hz: int,
        cognition_hz: int,
        observation_hz: int | None = None,
        render_hz: int | None = None,
    ) -> "ExecutionRates":
        physics = int(physics_hz)
        cognition = int(cognition_hz)
        if physics < 1:
            raise ValueError("physics_hz must be positive")
        if cognition < 1 or cognition > physics:
            raise ValueError("cognition_hz must be within [1, physics_hz]")
        if physics % cognition != 0:
            raise ValueError("physics_hz must be an integer multiple of cognition_hz")

        observation = min(12, cognition) if observation_hz is None else int(observation_hz)
        if observation < 1 or observation > cognition:
            raise ValueError("observation_hz must be within [1, cognition_hz]")

        render = min(60, physics) if render_hz is None else int(render_hz)
        if render < 1 or render > physics:
            raise ValueError("render_hz must be within [1, physics_hz]")

        return cls(
            physics_hz=physics,
            cognition_hz=cognition,
            observation_hz=observation,
            render_hz=render,
        )

    @property
    def physics_substeps_per_cognition(self) -> int:
        return self.physics_hz // self.cognition_hz

    def observation_due(self, tick: int, *, force: bool = False) -> bool:
        """Sample at the requested long-run rate without fractional timers."""
        if force:
            return True
        current = max(0, int(tick))
        if current == 0:
            return False
        return (
            current * self.observation_hz // self.cognition_hz
            != (current - 1) * self.observation_hz // self.cognition_hz
        )
