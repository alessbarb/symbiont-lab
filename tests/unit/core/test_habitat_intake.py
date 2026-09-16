import pytest

from symbiont.core.ecology import SharedHabitat
from symbiont.core.runtime import OrganismRuntime


def test_runtime_intake_is_limited_by_shared_habitat_resource() -> None:
    habitat = SharedHabitat(habitat_id="h", capacity=2, resources=3.0)
    runtime = OrganismRuntime(organism_id="a", habitat=habitat)
    runtime.metabolism.charge("maintenance", 1.0)
    assert runtime.request_resource_intake(0.75) == 0.75
    assert runtime.request_resource_intake(0.75) == 0.25
    assert habitat.snapshot().available_resources == 0.5


def test_intake_requires_habitat_and_positive_amount() -> None:
    runtime = OrganismRuntime()
    with pytest.raises(ValueError):
        runtime.request_resource_intake(0.1)
    habitat = SharedHabitat(habitat_id="h", capacity=1, resources=1.0)
    runtime = OrganismRuntime(organism_id="a", habitat=habitat)
    with pytest.raises(ValueError):
        runtime.request_resource_intake(0.0)
