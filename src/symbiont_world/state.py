"""WorldState and atomic tick commit/rollback (docs/design §3 inv. 7, §5).

Observation failure is tolerated (handled by the caller before it ever
reaches this module: a missing signal just becomes an absent key in
WorldObservation). A world state transition failure must never leave
partial causality committed — either the whole tick applies, or none of
it does and the tick is not counted.
"""
from __future__ import annotations

from copy import deepcopy

from .topology import OccupancyGrid, WorldBody


class TickAborted(Exception):
    """Raised by kernel code inside a tick transaction to signal that the
    world state transition failed; the transaction rolls back and the
    tick does not advance."""


class WorldState:
    """Owns everything a tick transaction must roll back atomically:
    occupancy and the per-organism WorldBody registry. Anything mutated by
    kernel code during a tick (§12: movement resolution mutates WorldBody
    in place) must live here, or an abort leaves partial causality behind
    (§3 inv. 7)."""

    def __init__(
        self,
        *,
        world_id: str,
        occupancy: OccupancyGrid | None = None,
        bodies: dict[str, WorldBody] | None = None,
    ) -> None:
        self.world_id = world_id
        self.tick = 0
        self.occupancy = occupancy or OccupancyGrid()
        self.bodies: dict[str, WorldBody] = bodies if bodies is not None else {}

    def begin_tick(self) -> "TickTransaction":
        return TickTransaction(self)


class TickTransaction:
    """Context manager: stages mutations against a snapshot; commits
    (advances tick) only if the block completes without TickAborted."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._snapshot_occupancy: OccupancyGrid | None = None
        self._snapshot_bodies: dict[str, WorldBody] | None = None
        self._snapshot_tick: int | None = None

    def __enter__(self) -> WorldState:
        self._snapshot_occupancy = deepcopy(self._state.occupancy)
        self._snapshot_bodies = deepcopy(self._state.bodies)
        self._snapshot_tick = self._state.tick
        return self._state

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self._state.tick = self._snapshot_tick + 1
            return False
        if issubclass(exc_type, TickAborted):
            self._state.occupancy = self._snapshot_occupancy
            self._state.bodies = self._snapshot_bodies
            self._state.tick = self._snapshot_tick
            return True
        return False
