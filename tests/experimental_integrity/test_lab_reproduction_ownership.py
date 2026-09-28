"""Population authority is an apparatus capability, never subject authority."""

import inspect

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont_lab.reproduction import HabitatBirthAuthority


@pytest.mark.parametrize("runtime_type", [OrganismRuntime, ModeledOrganismRuntime])
def test_subject_cannot_receive_population_authority(runtime_type):
    authority = HabitatBirthAuthority(habitat_id="boundary", capacity=2)
    before = authority.checkpoint()
    with pytest.raises(TypeError):
        runtime_type(birth_authority=authority)
    assert authority.checkpoint() == before


def test_population_records_and_authority_have_only_lab_ownership():
    from symbiont_lab.reproduction import BirthRecord, DeathRecord

    for owner in (BirthRecord, DeathRecord, HabitatBirthAuthority):
        assert inspect.getmodule(owner).__name__.startswith("symbiont_lab.")


@pytest.mark.parametrize("runtime_type", [OrganismRuntime, ModeledOrganismRuntime])
def test_ready_subject_does_not_register_or_create_population(runtime_type):
    authority = HabitatBirthAuthority(habitat_id="boundary", capacity=2)
    runtime = runtime_type(bootstrap_semantic_senses=False, discover_senses=False)
    runtime.living_body_state.growth_progress = 1.0
    assert runtime.reproductively_ready
    runtime.tick()
    assert authority.live_ids == ()
    assert authority.lineage_records == ()
    # No population authority is retained even after an explicit Lab admission.
    authority.register_runtime(runtime)
    assert all(value is not authority for value in vars(runtime).values())
