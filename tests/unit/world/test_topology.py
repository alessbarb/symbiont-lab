import pytest

from symbiont_world.topology import HexCoord, HexTopology, OccupancyGrid, WorldBody


def test_hex_neighbor_and_distance_roundtrip():
    origin = HexCoord(3, 3)
    for direction in range(6):
        neighbor = origin.neighbor(direction)
        assert origin.distance(neighbor) == 1


def test_hex_distance_is_symmetric_and_zero_for_self():
    a, b = HexCoord(0, 0), HexCoord(4, -2)
    assert a.distance(b) == b.distance(a)
    assert a.distance(a) == 0


def test_invalid_direction_rejected():
    with pytest.raises(ValueError):
        HexCoord(0, 0).neighbor(6)


def test_reflecting_boundary_blocks_move_out_of_bounds():
    topo = HexTopology(width=4, height=4)
    edge = HexCoord(3, 0)
    result, moved = topo.resolve_move(edge, direction=0)  # +q, off the east edge
    assert moved is False
    assert result == edge


def test_move_inside_bounds_succeeds():
    topo = HexTopology(width=4, height=4)
    origin = HexCoord(1, 1)
    result, moved = topo.resolve_move(origin, direction=0)
    assert moved is True
    assert topo.in_bounds(result)


def test_boundary_is_not_toroidal():
    topo = HexTopology(width=4, height=4)
    # Leaving from q=0 moving in the -q direction (west) must fail, not
    # wrap around to q=width-1.
    origin = HexCoord(0, 1)
    result, moved = topo.resolve_move(origin, direction=3)
    assert moved is False
    assert result == origin


def test_occupancy_grid_rejects_second_organism_in_same_cell():
    grid = OccupancyGrid()
    cell = HexCoord(2, 2)
    assert grid.occupy(cell, "org-a") is True
    assert grid.occupy(cell, "org-b") is False
    assert grid.occupant(cell) == "org-a"


def test_occupancy_grid_rejects_same_organism_occupying_twice():
    grid = OccupancyGrid()
    assert grid.occupy(HexCoord(0, 0), "org-a") is True
    assert grid.occupy(HexCoord(1, 0), "org-a") is False


def test_occupancy_move_frees_origin_cell():
    grid = OccupancyGrid()
    origin, target = HexCoord(0, 0), HexCoord(1, 0)
    grid.occupy(origin, "org-a")
    assert grid.move("org-a", target) is True
    assert grid.occupant(origin) is None
    assert grid.occupant(target) == "org-a"


def test_occupancy_move_blocked_if_target_taken():
    grid = OccupancyGrid()
    origin, target = HexCoord(0, 0), HexCoord(1, 0)
    grid.occupy(origin, "org-a")
    grid.occupy(target, "org-b")
    assert grid.move("org-a", target) is False


def test_world_body_defaults_emission_origin_to_occupied_cell():
    body = WorldBody(organism_id="org-a", occupied_cell=HexCoord(1, 1))
    assert body.emission_origin == body.occupied_cell
