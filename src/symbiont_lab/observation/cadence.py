"""Deterministic execution/observation/render cadence planning."""

from __future__ import annotations

from dataclasses import dataclass


def _best_divisor(source_hz: int, target_hz: int) -> int:
    """Highest exact divisor of source_hz not exceeding target_hz."""
    ceiling = max(1, min(int(source_hz), int(target_hz)))
    for candidate in range(ceiling, 0, -1):
        if source_hz % candidate == 0:
            return candidate
    return 1


@dataclass(frozen=True, slots=True)
class ExecutionRates:
    """Four independent clocks with deterministic integer relationships."""

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

        if observation_hz is None:
            # Scientific observer target: 10-20 Hz where the cognition rate
            # permits it; exact divisibility keeps sampling deterministic.
            observation = _best_divisor(cognition, min(20, cognition))
        else:
            observation = int(observation_hz)
            if observation < 1 or observation > cognition:
                raise ValueError("observation_hz must be within [1, cognition_hz]")
            if cognition % observation != 0:
                raise ValueError("cognition_hz must be an integer multiple of observation_hz")

        if render_hz is None:
            # Presentation target: up to 60 Hz, again as an exact solver divisor.
            render = _best_divisor(physics, min(60, physics))
        else:
            render = int(render_hz)
            if render < 1 or render > physics:
                raise ValueError("render_hz must be within [1, physics_hz]")
            if physics % render != 0:
                raise ValueError("physics_hz must be an integer multiple of render_hz")

        return cls(
            physics_hz=physics,
            cognition_hz=cognition,
            observation_hz=observation,
            render_hz=render,
        )

    @property
    def physics_substeps_per_cognition(self) -> int:
        return self.physics_hz // self.cognition_hz

    @property
    def cognition_ticks_per_observation(self) -> int:
        return self.cognition_hz // self.observation_hz

    @property
    def physics_substeps_per_render(self) -> int:
        return self.physics_hz // self.render_hz

    def observation_due(self, tick: int, *, force: bool = False) -> bool:
        if force:
            return True
        return int(tick) % self.cognition_ticks_per_observation == 0
