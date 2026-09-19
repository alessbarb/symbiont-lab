import pytest

from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from symbiont_world.topology import HexCoord

FIELD_ID = "f01a4b7eb3833241"
RESOURCE_ID = "r7c2e9a1b4d80556"
HAZARD_ID = "h9f3d1c8a2e60734"


def _ground_truth() -> GroundTruth:
    return GroundTruth(
        fields={FIELD_ID: PeriodicFieldLaw(amplitude=1.0, bias=0.0, angular_frequency=0.2)},
        resources={RESOURCE_ID: ResourceLaw(capacity=10.0, renewal_rate=0.5, decay_rate=0.1, initial_quantity=5.0)},
        hazards={HAZARD_ID: HazardLaw(base_probability=0.1, density_coupling=1.0)},
    )


def test_ground_truth_contains_no_domain_names():
    truth = _ground_truth()
    assert set(truth.fields) == {FIELD_ID}
    assert set(truth.resources) == {RESOURCE_ID}
    assert set(truth.hazards) == {HAZARD_ID}
    for name in ("temperature", "food", "humidity", "toxicity", "contamination"):
        assert name not in truth.fields
        assert name not in truth.resources
        assert name not in truth.hazards


def test_hazard_exposures_keyed_by_opaque_hazard_id():
    env = WorldEnvironment(_ground_truth())
    exposures = env.hazard_exposures(local_density=0.5)
    assert set(exposures) == {HAZARD_ID}
    assert exposures[HAZARD_ID] == pytest.approx(0.1 * (1.0 + 1.0 * 0.5))


def test_hazard_exposures_has_no_persistent_state_across_calls():
    env = WorldEnvironment(_ground_truth())
    first = env.hazard_exposures(local_density=0.3)
    second = env.hazard_exposures(local_density=0.3)
    assert first == second


def test_field_values_are_deterministic_for_same_tick():
    env = WorldEnvironment(_ground_truth())
    env.propagate_fields(tick=10)
    a = dict(env.field_values())
    env.propagate_fields(tick=10)
    b = dict(env.field_values())
    assert a == b


def test_cell_is_not_materialized_before_first_access():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(3, 3)
    assert not env.is_materialized(cell)
    env.resource_pool(cell)
    assert env.is_materialized(cell)


def test_lazy_initial_quantity_matches_law():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(1, 1)
    pool = env.resource_pool(cell)
    assert pool[RESOURCE_ID] == 5.0


def test_renew_resources_moves_pool_toward_capacity():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(0, 0)
    env.renew_resources(cell)
    pool = env.resource_pool(cell)
    assert 0.0 <= pool[RESOURCE_ID] <= 10.0


def test_acquire_depletes_pool_without_going_negative():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(2, 2)
    granted = env.acquire(cell, RESOURCE_ID, requested=3.0)
    assert granted == 3.0
    assert env.resource_pool(cell)[RESOURCE_ID] == pytest.approx(2.0)


def test_acquire_more_than_available_is_capped_at_pool_size():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(4, 4)
    granted = env.acquire(cell, RESOURCE_ID, requested=100.0)
    assert granted == 5.0
    assert env.resource_pool(cell)[RESOURCE_ID] == 0.0


def test_acquire_never_yields_negative_pool_across_repeated_calls():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(5, 5)
    for _ in range(10):
        env.acquire(cell, RESOURCE_ID, requested=3.0)
    assert env.resource_pool(cell)[RESOURCE_ID] == 0.0


def test_acquire_rejects_negative_request():
    env = WorldEnvironment(_ground_truth())
    with pytest.raises(ValueError):
        env.acquire(HexCoord(0, 0), RESOURCE_ID, requested=-1.0)


def test_resource_pool_and_field_values_return_snapshots_not_live_references():
    env = WorldEnvironment(_ground_truth())
    cell = HexCoord(0, 0)
    pool = env.resource_pool(cell)
    with pytest.raises(TypeError):
        pool[RESOURCE_ID] = 999.0



def test_resource_renewal_factor_scales_positive_recovery():
    env_fast = WorldEnvironment(_ground_truth())
    env_slow = WorldEnvironment(_ground_truth())
    cell = HexCoord(0, 0)

    env_fast.acquire(cell, RESOURCE_ID, requested=4.0)
    env_slow.acquire(cell, RESOURCE_ID, requested=4.0)

    env_fast.renew_resources(cell, renewal_factor=1.0)
    env_slow.renew_resources(cell, renewal_factor=0.25)

    assert env_fast.resource_pool(cell)[RESOURCE_ID] > env_slow.resource_pool(cell)[RESOURCE_ID]


def test_resource_renewal_factor_rejects_negative_values():
    env = WorldEnvironment(_ground_truth())
    with pytest.raises(ValueError):
        env.renew_resources(HexCoord(0, 0), renewal_factor=-0.1)
