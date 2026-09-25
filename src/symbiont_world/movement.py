"""W1 movement resolution (docs/design/symbiont-world-v1.md §12.2, §5).

Must run inside a WorldState.begin_tick() transaction: any inconsistency
raises TickAborted so the caller's transaction rolls back the whole tick,
not just the affected organism's move (§3 inv. 7).
"""

from __future__ import annotations

from typing import Mapping

from .rng import derive_world_rng
from .state import TickAborted
from .topology import BodyPlacement, HexCoord, HexTopology, OccupancyGrid


def resolve_movement(
    topology: HexTopology,
    occupancy: OccupancyGrid,
    bodies: Mapping[str, BodyPlacement],
    intents: Mapping[str, int | None],
    *,
    world_seed: int,
    tick: int,
) -> None:
    """intents maps organism_id -> direction (0..5) or None to rest.

    Resolution never depends on dict/intent iteration order: contenders for
    the same target cell are ordered by organism_id before a deterministic,
    RNG-namespaced tie-break (§5, simultaneous intent resolution).
    """
    proposals: dict[HexCoord, list[str]] = {}
    for organism_id, direction in intents.items():
        if direction is None:
            continue
        body = bodies.get(organism_id)
        if body is None:
            raise TickAborted(f"movement intent for unknown organism {organism_id!r}")
        target, moved = topology.resolve_move(body.occupied_cell, direction)
        if not moved:
            continue
        proposals.setdefault(target, []).append(organism_id)

    rng = derive_world_rng(world_seed, f"resolution.simultaneous-intent:{tick}")
    for target in sorted(proposals, key=lambda c: (c.q, c.r)):
        contenders = proposals[target]
        if occupancy.is_occupied(target):
            continue
        winner = contenders[0] if len(contenders) == 1 else rng.choice(sorted(contenders))
        if not occupancy.move(winner, target):
            raise TickAborted(f"occupancy invariant violated moving {winner!r} to {target!r}")
        bodies[winner].occupied_cell = target
        bodies[winner].emission_origin = target
