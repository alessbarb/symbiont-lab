"""W1 local observation pipeline (docs/design/symbiont-world-v1.md §12.1).

No real fields/resources exist yet (deferred to W2's Genesis ground truth).
This only exercises ObservableSource -> WorldObservation end to end with a
single synthetic, opaque signal: local occupancy density around a body.
"""

from __future__ import annotations

from hashlib import sha256

from .contracts import WorldObservation
from .genesis import WorldEnvironment
from .topology import BodyPlacement, HexCoord, HexTopology, OccupancyGrid


def opaque_signal_id(label: str) -> str:
    """Stable hash of an apparatus-only label. The label itself never
    reaches WorldObservation -- only its hash does (docs/design §3 inv. 1)."""
    return sha256(f"symbiont-world:signal:{label}".encode("utf-8")).hexdigest()[:16]


LOCAL_OCCUPANCY_SIGNAL = opaque_signal_id("local-occupancy-density")
_LOCAL_OCCUPANCY_SIGNAL = LOCAL_OCCUPANCY_SIGNAL


def local_observation(
    topology: HexTopology,
    occupancy: OccupancyGrid,
    body: BodyPlacement,
    environment: WorldEnvironment | None = None,
) -> WorldObservation:
    visited: set[HexCoord] = {body.occupied_cell}
    frontier: set[HexCoord] = {body.occupied_cell}
    occupied_neighbors = 0
    total_neighbors = 0

    for _ in range(max(body.interaction_radius, 0)):
        next_frontier: set[HexCoord] = set()
        for cell in frontier:
            for direction in range(6):
                neighbor = cell.neighbor(direction)
                if neighbor in visited or not topology.in_bounds(neighbor):
                    continue
                visited.add(neighbor)
                next_frontier.add(neighbor)
                total_neighbors += 1
                if occupancy.is_occupied(neighbor):
                    occupied_neighbors += 1
        frontier = next_frontier

    density = occupied_neighbors / total_neighbors if total_neighbors else 0.0
    signals: dict[str, float] = {_LOCAL_OCCUPANCY_SIGNAL: density}

    if environment is not None:
        signals.update(environment.field_values())
        signals.update(environment.resource_pool(body.occupied_cell))
        signals.update(environment.hazard_exposures_at(body.occupied_cell, density))

    return WorldObservation(signals=signals)
