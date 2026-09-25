from symbiont_world.checkpoint import restore, take_checkpoint
from symbiont_world.rng import derive_world_rng
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord


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
