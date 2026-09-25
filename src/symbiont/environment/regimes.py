from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world import HostProfile


@dataclass(slots=True, frozen=True)
class RegimeTransition:
    step: int
    fraction: float
    magnitude: float
    affected_hosts: frozenset[int]


def apply_regime_shift(
    profiles: list[HostProfile],
    rng: random.Random,
    *,
    fraction: float = 0.35,
    magnitude: float = 0.22,
) -> set[int]:
    """Change the benign baseline of a subset of synthetic hosts.

    This is concept drift, not an attack. Agents are not told which hosts changed.
    """

    count = min(len(profiles), max(0, round(len(profiles) * max(0.0, min(fraction, 1.0)))))
    selected = set(rng.sample(range(len(profiles)), count)) if count else set()
    magnitude = max(0.0, min(magnitude, 0.60))
    for index in selected:
        profile = profiles[index]
        profile.cpu = min(0.85, profile.cpu + magnitude * 0.35)
        profile.network = min(0.90, profile.network + magnitude)
        profile.file_changes = min(0.75, profile.file_changes + magnitude * 0.60)
        profile.new_processes = min(0.65, profile.new_processes + magnitude * 0.40)
        profile.persistence_changes = min(0.20, profile.persistence_changes + magnitude * 0.08)
    return selected
