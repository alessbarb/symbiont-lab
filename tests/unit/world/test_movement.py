import pytest

from symbiont_world.movement import resolve_movement
from symbiont_world.state import TickAborted, WorldState
from symbiont_world.topology import BodyPlacement, HexCoord, HexTopology, OccupancyGrid


def _setup(*placements: tuple[str, HexCoord]) -> tuple[HexTopology, OccupancyGrid, dict]:
    topo = HexTopology(width=8, height=8)
    grid = OccupancyGrid()
    bodies = {}
    for organism_id, cell in placements:
        grid.occupy(cell, organism_id)
        bodies[organism_id] = BodyPlacement(organism_id=organism_id, occupied_cell=cell)
    return topo, grid, bodies


def test_single_organism_moves_to_free_cell():
    topo, grid, bodies = _setup(("org-a", HexCoord(1, 1)))
    resolve_movement(topo, grid, bodies, {"org-a": 0}, world_seed=101, tick=0)
    assert bodies["org-a"].occupied_cell == HexCoord(2, 1)
    assert grid.occupant(HexCoord(2, 1)) == "org-a"
    assert grid.occupant(HexCoord(1, 1)) is None


def test_move_across_boundary_is_rejected_and_organism_stays():
    topo = HexTopology(width=4, height=4)
    grid = OccupancyGrid()
    edge = HexCoord(3, 0)
    grid.occupy(edge, "org-a")
    bodies = {"org-a": BodyPlacement(organism_id="org-a", occupied_cell=edge)}
    resolve_movement(topo, grid, bodies, {"org-a": 0}, world_seed=101, tick=0)
    assert bodies["org-a"].occupied_cell == edge
    assert grid.occupant(edge) == "org-a"


def test_resting_organism_is_unaffected():
    topo, grid, bodies = _setup(("org-a", HexCoord(1, 1)))
    resolve_movement(topo, grid, bodies, {"org-a": None}, world_seed=101, tick=0)
    assert bodies["org-a"].occupied_cell == HexCoord(1, 1)


def test_two_organisms_converging_on_same_cell_pick_exactly_one_winner():
    target = HexCoord(2, 0)
    topo, grid, bodies = _setup(("org-a", HexCoord(1, 0)), ("org-b", HexCoord(3, -1)))
    intents = {"org-a": 0, "org-b": 4}
    assert bodies["org-a"].occupied_cell.neighbor(0) == target
    assert bodies["org-b"].occupied_cell.neighbor(4) == target

    resolve_movement(topo, grid, bodies, intents, world_seed=101, tick=5)
    winners = [oid for oid, body in bodies.items() if body.occupied_cell == target]
    assert len(winners) == 1
    assert grid.occupant(target) in {"org-a", "org-b"}


def test_simultaneous_intent_resolution_is_deterministic_for_same_seed_and_tick():
    target = HexCoord(2, 0)

    def run():
        topo, grid, bodies = _setup(("org-a", HexCoord(1, 0)), ("org-b", HexCoord(3, -1)))
        resolve_movement(topo, grid, bodies, {"org-a": 0, "org-b": 4}, world_seed=101, tick=5)
        return next(oid for oid, body in bodies.items() if body.occupied_cell == target)

    assert run() == run()


def test_occupied_target_blocks_all_contenders():
    target = HexCoord(2, 0)
    topo, grid, bodies = _setup(
        ("org-a", HexCoord(1, 0)), ("org-b", HexCoord(3, -1)), ("org-c", target)
    )
    resolve_movement(topo, grid, bodies, {"org-a": 0, "org-b": 4}, world_seed=101, tick=0)
    assert bodies["org-a"].occupied_cell == HexCoord(1, 0)
    assert bodies["org-b"].occupied_cell == HexCoord(3, -1)
    assert grid.occupant(target) == "org-c"


def test_movement_intent_for_unknown_organism_aborts():
    topo, grid, bodies = _setup(("org-a", HexCoord(1, 1)))
    with pytest.raises(TickAborted):
        resolve_movement(topo, grid, bodies, {"ghost": 0}, world_seed=101, tick=0)


def test_aborted_movement_rolls_back_whole_tick_not_just_the_offender():
    topo, grid, bodies = _setup(("org-a", HexCoord(1, 1)))
    state = WorldState(world_id="genesis", occupancy=grid, bodies=bodies)
    with state.begin_tick():
        resolve_movement(topo, state.occupancy, state.bodies, {"org-a": 0}, world_seed=101, tick=0)
        resolve_movement(topo, state.occupancy, state.bodies, {"ghost": 0}, world_seed=101, tick=0)
    assert state.tick == 0
    assert state.occupancy.occupant(HexCoord(1, 1)) == "org-a"
    assert state.occupancy.occupant(HexCoord(2, 1)) is None
    assert state.bodies["org-a"].occupied_cell == HexCoord(1, 1)
