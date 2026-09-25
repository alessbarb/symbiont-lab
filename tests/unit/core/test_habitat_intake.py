import pytest
from symbiont.core.ecology import SharedHabitat
from symbiont.core.runtime import OrganismRuntime


def test_runtime_intake_is_limited_by_shared_habitat_resource() -> None:
    habitat = SharedHabitat(habitat_id="h", capacity=2, resources=3.0)
    runtime = OrganismRuntime(organism_id="a", habitat=habitat)
    runtime.metabolism.charge("maintenance", 1.0)
    assert runtime.request_resource_intake(0.75) == 0.75
    assert runtime.request_resource_intake(0.75) == 0.25
    # Membership consumes no physical stock. Only accepted intake depletes
    # the habitat, and body headroom bounds the second request.
    assert habitat.snapshot().available_resources == pytest.approx(2.0)


def test_intake_requires_habitat_and_positive_amount() -> None:
    runtime = OrganismRuntime()
    with pytest.raises(ValueError):
        runtime.request_resource_intake(0.1)
    habitat = SharedHabitat(habitat_id="h", capacity=1, resources=1.0)
    runtime = OrganismRuntime(organism_id="a", habitat=habitat)
    with pytest.raises(ValueError):
        runtime.request_resource_intake(0.0)


def test_untyped_absorption_needs_no_habitat_and_exposes_no_resource_identity() -> None:
    runtime = OrganismRuntime(organism_id="body")
    before = runtime.metabolism.snapshot()
    runtime.metabolism.charge("maintenance", 0.4)
    runtime.metabolism.charge("cognition", 0.2)

    absorbed = runtime.absorb_metabolic_energy(0.3)
    after = runtime.metabolism.snapshot()

    assert absorbed == pytest.approx(0.3)
    assert sum(after.reserve.values()) > sum(before.reserve.values()) - 0.6
    assert runtime._resource_habitats == {}


def test_untyped_absorption_is_bounded_by_total_internal_deficit() -> None:
    runtime = OrganismRuntime(organism_id="body")
    assert runtime.absorb_metabolic_energy(1.0) == 0.0
    runtime.metabolism.charge("maintenance", 0.1)
    assert runtime.absorb_metabolic_energy(1.0) == pytest.approx(0.1)
