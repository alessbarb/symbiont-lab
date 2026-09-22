from __future__ import annotations

from dataclasses import dataclass


DEFAULT_SEEDS = (101, 127, 149, 163, 181, 197, 211, 227, 239, 251)


@dataclass(frozen=True, slots=True)
class Phase:
    name: str
    ticks: int


K1_PHASES = (
    Phase("baseline", 16),
    Phase("learning", 16),
    Phase("regime_change", 16),
    Phase("perturbation", 8),
    Phase("recovery", 16),
    Phase("absence", 8),
    Phase("reappearance", 16),
)


def phases(ticks_per_phase: int | None = None) -> tuple[Phase, ...]:
    if ticks_per_phase is None:
        return K1_PHASES
    if ticks_per_phase <= 0:
        raise ValueError("ticks_per_phase must be positive")
    return tuple(Phase(item.name, ticks_per_phase) for item in K1_PHASES)
