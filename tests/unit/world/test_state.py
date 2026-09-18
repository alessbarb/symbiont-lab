import pytest

from symbiont_world.state import TickAborted, WorldState
from symbiont_world.topology import HexCoord


def test_successful_tick_commits_and_advances():
    state = WorldState(world_id="genesis")
    with state.begin_tick() as tick_state:
        tick_state.occupancy.occupy(HexCoord(0, 0), "org-a")
    assert state.tick == 1
    assert state.occupancy.occupant(HexCoord(0, 0)) == "org-a"


def test_aborted_tick_rolls_back_occupancy_and_does_not_advance():
    state = WorldState(world_id="genesis")
    with state.begin_tick() as tick_state:
        tick_state.occupancy.occupy(HexCoord(0, 0), "org-a")
        raise TickAborted("resource competition resolution failed")
    assert state.tick == 0
    assert state.occupancy.occupant(HexCoord(0, 0)) is None


def test_no_partial_causality_survives_an_aborted_tick():
    state = WorldState(world_id="genesis")
    with state.begin_tick() as tick_state:
        tick_state.occupancy.occupy(HexCoord(0, 0), "org-a")
        tick_state.occupancy.occupy(HexCoord(1, 0), "org-b")
        raise TickAborted("field propagation inconsistent")
    assert state.occupancy.snapshot() == {}


def test_aborted_tick_rolls_back_body_registry_too():
    from symbiont_world.topology import WorldBody

    state = WorldState(world_id="genesis")
    body = WorldBody(organism_id="org-a", occupied_cell=HexCoord(0, 0))
    state.occupancy.occupy(body.occupied_cell, "org-a")
    state.bodies["org-a"] = body

    with state.begin_tick() as tick_state:
        tick_state.bodies["org-a"].occupied_cell = HexCoord(5, 5)
        raise TickAborted("movement resolution failed")

    assert state.bodies["org-a"].occupied_cell == HexCoord(0, 0)


def test_unrelated_exception_propagates_without_swallowing():
    state = WorldState(world_id="genesis")
    with pytest.raises(RuntimeError):
        with state.begin_tick():
            raise RuntimeError("not a modeled tick failure")
    assert state.tick == 0
