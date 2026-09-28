"""Public World checkpoints preserve deterministic movement continuation."""

from symbiont_world.checkpoint import restore, take_checkpoint
from symbiont_world.movement import resolve_movement
from symbiont_world.state import WorldState
from symbiont_world.topology import BodyPlacement, HexCoord, HexTopology


def test_restored_world_matches_uninterrupted_movement_trajectory():
    original = WorldState(world_id="movement-checkpoint")
    for organism_id, cell in (("a", HexCoord(1, 1)), ("b", HexCoord(3, 1))):
        original.bodies[organism_id] = BodyPlacement(organism_id, cell, 3, 2)
        original.occupancy.occupy(cell, organism_id)
    original.tick = 7
    checkpoint = take_checkpoint(original, constitution_fingerprint="world", rng_states={})
    resumed = restore(checkpoint)
    topology = HexTopology(8, 8)

    # The first step includes a seeded tie-break for the same target cell.
    for intents in ({"a": 0, "b": 3}, {"a": 5, "b": 5}, {"a": 0, "b": 0}):
        previous_tick = original.tick
        for state in (original, resumed):
            with state.begin_tick():
                resolve_movement(
                    topology,
                    state.occupancy,
                    state.bodies,
                    intents,
                    world_seed=101,
                    tick=state.tick,
                )
        # A missing registry must not silently roll back the resumed tick.
        assert original.tick == resumed.tick == previous_tick + 1
        assert original.occupancy.snapshot() == resumed.occupancy.snapshot()
        assert original.bodies == resumed.bodies

    assert restore(checkpoint).tick == 7
    assert restore(checkpoint).bodies["a"].occupied_cell == HexCoord(1, 1)
    assert restore(checkpoint).bodies["b"].occupied_cell == HexCoord(3, 1)
