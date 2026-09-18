"""World checkpoint/restore: checkpoint -> restore -> identical future.

Bounded descriptive state only, per the repo-wide checkpoint contract:
world_id, tick, constitution fingerprint, occupancy and RNG stream states.
No raw telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .state import WorldState
from .topology import HexCoord, OccupancyGrid


@dataclass(frozen=True, slots=True)
class WorldCheckpoint:
    world_id: str
    tick: int
    constitution_fingerprint: str
    occupancy: Mapping[HexCoord, str]
    rng_states: Mapping[str, tuple]

    def __post_init__(self) -> None:
        object.__setattr__(self, "occupancy", MappingProxyType(dict(self.occupancy)))
        object.__setattr__(self, "rng_states", MappingProxyType(dict(self.rng_states)))


def take_checkpoint(
    state: WorldState,
    *,
    constitution_fingerprint: str,
    rng_states: Mapping[str, tuple],
) -> WorldCheckpoint:
    return WorldCheckpoint(
        world_id=state.world_id,
        tick=state.tick,
        constitution_fingerprint=constitution_fingerprint,
        occupancy=state.occupancy.snapshot(),
        rng_states=rng_states,
    )


def restore(checkpoint: WorldCheckpoint) -> WorldState:
    grid = OccupancyGrid()
    for cell, organism_id in checkpoint.occupancy.items():
        grid.occupy(cell, organism_id)
    state = WorldState(world_id=checkpoint.world_id, occupancy=grid)
    state.tick = checkpoint.tick
    return state
