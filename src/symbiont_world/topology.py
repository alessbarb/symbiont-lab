"""Hex topology, spatial embodiment and occupancy (docs/design §5, §7).

Reflecting/impermeable boundary, not toroidal: a move that would cross the
edge fails rather than wrapping. One organism per cell, at most.
"""
from __future__ import annotations

from dataclasses import dataclass

# Axial hex coordinates, pointy-top, six directions clockwise from east.
_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
)


@dataclass(frozen=True, slots=True)
class HexCoord:
    q: int
    r: int

    def neighbor(self, direction: int) -> "HexCoord":
        if not 0 <= direction < 6:
            raise ValueError("direction must be in 0..5")
        dq, dr = _DIRECTIONS[direction]
        return HexCoord(self.q + dq, self.r + dr)

    def distance(self, other: "HexCoord") -> int:
        dq = self.q - other.q
        dr = self.r - other.r
        return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


@dataclass(slots=True)
class BodyPlacement:
    """What the world knows about where a body is placed in physical space (AUD-003, AUD-015).

    The World state does not possess a second biological Body; it tracks the spatial
    placement, cell occupancy and orientation of the organism's Body.
    """

    organism_id: str
    occupied_cell: HexCoord
    orientation_state: int = 0
    interaction_radius: int = 1
    emission_origin: HexCoord | None = None

    def __post_init__(self) -> None:
        if self.emission_origin is None:
            self.emission_origin = self.occupied_cell

    @property
    def body_id(self) -> str:
        return self.organism_id



class HexTopology:
    """A finite hex grid with a reflecting (non-toroidal) boundary."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError("world dimensions must be positive")
        self.width = width
        self.height = height

    def in_bounds(self, coord: HexCoord) -> bool:
        return 0 <= coord.q < self.width and 0 <= coord.r < self.height

    def resolve_move(self, origin: HexCoord, direction: int) -> tuple[HexCoord, bool]:
        """Returns (resulting_cell, moved). A move across the boundary
        fails and leaves the body at `origin`; the caller may still
        charge the action's cost (docs/design §7, Frontera del mapa)."""
        target = origin.neighbor(direction)
        if not self.in_bounds(target):
            return origin, False
        return target, True


class OccupancyGrid:
    """Enforces the Genesis v1 rule: at most one live organism per cell."""

    def __init__(self) -> None:
        self._by_cell: dict[HexCoord, str] = {}
        self._by_organism: dict[str, HexCoord] = {}

    def is_occupied(self, cell: HexCoord) -> bool:
        return cell in self._by_cell

    def occupant(self, cell: HexCoord) -> str | None:
        return self._by_cell.get(cell)

    def cell_of(self, organism_id: str) -> HexCoord | None:
        return self._by_organism.get(organism_id)

    def occupy(self, cell: HexCoord, organism_id: str) -> bool:
        if organism_id in self._by_organism or cell in self._by_cell:
            return False
        self._by_cell[cell] = organism_id
        self._by_organism[organism_id] = cell
        return True

    def vacate(self, organism_id: str) -> None:
        cell = self._by_organism.pop(organism_id, None)
        if cell is not None:
            self._by_cell.pop(cell, None)

    def move(self, organism_id: str, target: HexCoord) -> bool:
        current = self._by_organism.get(organism_id)
        if current is None or target in self._by_cell:
            return False
        del self._by_cell[current]
        self._by_cell[target] = organism_id
        self._by_organism[organism_id] = target
        return True

    def snapshot(self) -> dict[HexCoord, str]:
        return dict(self._by_cell)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OccupancyGrid):
            return NotImplemented
        return self._by_cell == other._by_cell and self._by_organism == other._by_organism

