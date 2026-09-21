import pytest

from symbiont.core.ecology import SharedHabitat


def test_capacity_is_independent_from_physical_resource_stock():
    habitat = SharedHabitat(habitat_id="h", capacity=1, resources=1.0)

    assert habitat.admit("a")
    assert habitat.snapshot().available_resources == pytest.approx(1.0)
    assert not habitat.admit("b")

    assert habitat.release("a")
    assert habitat.snapshot().available_resources == pytest.approx(1.0)
    assert habitat.admit("b")


def test_checkpoint_round_trip():
    habitat = SharedHabitat(habitat_id="h", capacity=2, resources=2.0)
    assert habitat.admit("a")

    restored = SharedHabitat.from_checkpoint(habitat.checkpoint())

    assert restored.snapshot() == habitat.snapshot()
    assert restored.has_allocation("a")


def test_habitat_dynamics_change_intake_without_semantic_preferences():
    habitat = SharedHabitat(
        habitat_id="h",
        capacity=1,
        resources=2.0,
        renewal_rate=0.25,
        acquisition_cost=2.0,
        physiological_usefulness=1.5,
        information_content=0.75,
    )
    assert habitat.admit("a")
    assert habitat.consume("a", 0.2) == pytest.approx(0.3)
    assert habitat.snapshot().available_resources == pytest.approx(1.6)
    assert habitat.renew() == pytest.approx(0.25)
    assert habitat.snapshot().available_resources == pytest.approx(1.85)

    restored = SharedHabitat.from_checkpoint(habitat.checkpoint())
    assert restored.acquisition_cost == 2.0
    assert restored.physiological_usefulness == 1.5
    assert restored.information_content == 0.75


def test_release_never_regenerates_consumed_resource():
    habitat = SharedHabitat(habitat_id="h", capacity=1, resources=1.0)
    assert habitat.admit("a")
    assert habitat.consume("a", 0.4) == pytest.approx(0.4)
    assert habitat.release("a")
    assert habitat.snapshot().available_resources == pytest.approx(0.6)
