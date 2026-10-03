from environment.checkpoint import restore, take_checkpoint
from environment.rng import derive_world_rng
from environment.state import WorldState
from environment.topology import BodyPlacement, HexCoord


def _seed_state() -> WorldState:
    state = WorldState(world_id="genesis")
    state.occupancy.occupy(HexCoord(0, 0), "org-a")
    state.occupancy.occupy(HexCoord(1, 1), "org-b")
    state.tick = 42
    return state


def test_checkpoint_round_trips_occupancy_and_tick():
    state = _seed_state()
    checkpoint = take_checkpoint(
        state, constitution_fingerprint="abc123", rng_states={"resolution": ()}
    )
    restored = restore(checkpoint)
    assert restored.tick == state.tick
    assert restored.world_id == state.world_id
    assert restored.occupancy.snapshot() == state.occupancy.snapshot()


def test_checkpoint_occupancy_is_immutable_snapshot():
    state = _seed_state()
    checkpoint = take_checkpoint(state, constitution_fingerprint="abc123", rng_states={})
    state.occupancy.occupy(HexCoord(2, 2), "org-c")
    assert HexCoord(2, 2) not in checkpoint.occupancy


def test_restored_rng_state_produces_identical_future():
    rng = derive_world_rng(101, "resolution.simultaneous-intent")
    saved_state = rng.getstate()
    original_future = [rng.random() for _ in range(5)]

    restored_rng = derive_world_rng(101, "resolution.simultaneous-intent")
    restored_rng.setstate(saved_state)
    replayed_future = [restored_rng.random() for _ in range(5)]

    assert original_future == replayed_future


def _state_with_body() -> WorldState:
    state = WorldState(world_id="body-world")
    body = BodyPlacement("org-a", HexCoord(1, 1), 3, 2, HexCoord(1, 0))
    state.bodies[body.organism_id] = body
    state.occupancy.occupy(body.occupied_cell, body.organism_id)
    state.tick = 7
    return state


def test_checkpoint_round_trips_complete_body_placement():
    state = _state_with_body()
    checkpoint = take_checkpoint(state, constitution_fingerprint="body", rng_states={})

    restored = restore(checkpoint)

    assert restored.bodies == state.bodies
    assert restored.bodies["org-a"] is not state.bodies["org-a"]


def test_checkpoint_body_snapshot_is_independent_of_live_mutations():
    state = _state_with_body()
    checkpoint = take_checkpoint(state, constitution_fingerprint="body", rng_states={})
    state.bodies["org-a"].orientation_state = 5
    state.bodies["org-a"].interaction_radius = 4
    state.bodies["org-a"].occupied_cell = HexCoord(2, 1)
    state.bodies["org-a"].emission_origin = HexCoord(2, 0)
    state.bodies.clear()

    restored = restore(checkpoint)

    assert restored.bodies == _state_with_body().bodies


def test_restores_do_not_share_mutable_body_placements():
    checkpoint = take_checkpoint(_state_with_body(), constitution_fingerprint="body", rng_states={})
    first = restore(checkpoint)
    second = restore(checkpoint)
    first.bodies["org-a"].orientation_state = 5
    first.bodies["org-a"].interaction_radius = 4
    first.bodies["org-a"].occupied_cell = HexCoord(2, 1)
    first.bodies["org-a"].emission_origin = HexCoord(2, 0)
    first.bodies.clear()

    assert second.bodies == _state_with_body().bodies
    assert restore(checkpoint).bodies == second.bodies
