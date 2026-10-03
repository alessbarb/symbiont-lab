"""Lab-owned reproduction preserves energy, germinality, and population bookkeeping."""

import pytest

from lab.integration.organism import create_canonical_organism


def _reproduction_genome():
    import json
    from dataclasses import replace
    from importlib import resources

    from symbiont.cognition.genome import GenomeCodec

    payload = json.loads(
        resources.files("symbiont.genetics").joinpath("defaults/base-genome-v2.json").read_text()
    )
    return replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")


def test_materialized_birth_conserves_parent_child_energy() -> None:
    from lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud

    authority = HabitatBirthAuthority(habitat_id="h", capacity=2)
    parent = create_canonical_organism(
        organism_id="parent",
        genome=_reproduction_genome(),
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    parent.living_body_state.growth_progress = 1.0
    parent_before = parent.living_body_state.energy_reserve
    birth_energy = parent.ontogeny.reproduction_energy()

    child = materialize_clonal_bud(parent, authority=authority)

    assert child is not None
    assert child.generation == 1
    assert child.living_body_state.energy_reserve == pytest.approx(birth_energy)
    assert child.living_body_state.growth_progress == pytest.approx(0.0)
    assert parent.living_body_state.energy_reserve == pytest.approx(parent_before - birth_energy)
    assert (
        parent.living_body_state.energy_reserve + child.living_body_state.energy_reserve
        == pytest.approx(parent_before)
    )


def test_denied_birth_does_not_consume_parent_energy() -> None:
    from lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud

    authority = HabitatBirthAuthority(habitat_id="full", capacity=1)
    parent = create_canonical_organism(
        organism_id="parent",
        genome=_reproduction_genome(),
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    parent.living_body_state.growth_progress = 1.0
    before = parent.living_body_state.energy_reserve

    assert materialize_clonal_bud(parent, authority=authority) is None
    assert parent.living_body_state.energy_reserve == pytest.approx(before)
    assert authority.live_ids == ("parent",)


def test_materialized_child_is_germinal_and_not_cognitively_inherited() -> None:
    from lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud

    authority = HabitatBirthAuthority(habitat_id="h", capacity=2)
    parent = create_canonical_organism(
        organism_id="parent",
        genome=_reproduction_genome(),
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    parent.living_body_state.growth_progress = 1.0

    child = materialize_clonal_bud(parent, authority=authority)

    assert child is not None
    assert child.organism_id != parent.organism_id
    assert child.generation == 1
    assert child.cognitive_bridge is not None
    assert child.tick_count == 0
    assert child.living_body_state.growth_progress == pytest.approx(0.0)
    assert not child.reproductively_ready


def test_materialized_child_can_join_parent_social_habitat() -> None:
    from lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud
    from symbiont.core.social import SocialHabitat
    from symbiont.core.social.interactions import EcologicalResourcePool

    authority = HabitatBirthAuthority(habitat_id="h", capacity=2)
    social = SocialHabitat(EcologicalResourcePool({"food": 3.0}), max_members=3)
    social.admit("peer")
    parent = create_canonical_organism(
        organism_id="parent",
        genome=_reproduction_genome(),
        social_habitat=social,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    assert parent.join_social_habitat(social)
    parent.living_body_state.growth_progress = 1.0

    child = materialize_clonal_bud(parent, authority=authority)

    assert child is not None
    assert child.social_habitat is social
    assert child.join_social_habitat(social)
    assert child.organism_id in social.members


def test_birth_uses_parent_energy_not_shared_habitat_resource_stock() -> None:
    from lab.reproduction import HabitatBirthAuthority, materialize_clonal_bud
    from symbiont.core.social.ecology import SharedHabitat

    authority = HabitatBirthAuthority(habitat_id="h", capacity=2)
    surface = SharedHabitat(
        habitat_id="physical-surface",
        capacity=2,
        resources=0.0,
    )
    parent = create_canonical_organism(
        organism_id="parent",
        genome=_reproduction_genome(),
        resource_habitats={"opaque": surface},
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(parent)
    parent.living_body_state.growth_progress = 1.0
    before = parent.living_body_state.energy_reserve

    child = materialize_clonal_bud(parent, authority=authority)

    assert child is not None
    assert surface.snapshot().population == 2
    assert surface.snapshot().available_resources == pytest.approx(0.0)
    assert (
        parent.living_body_state.energy_reserve + child.living_body_state.energy_reserve
        == pytest.approx(before)
    )


def test_lab_observes_death_and_releases_population_slot_once() -> None:
    from lab.reproduction import HabitatBirthAuthority
    from symbiont.core.embodiment.metabolism import MetabolicLedger
    from symbiont.core.orchestration.runtime import OrganismDeadError

    authority = HabitatBirthAuthority(habitat_id="h", capacity=1)
    metabolism = MetabolicLedger(
        replenishment={
            kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")
        }
    )
    runtime = create_canonical_organism(
        organism_id="parent",
        metabolism=metabolism,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    authority.register_runtime(runtime)
    metabolism.charge("maintenance", 4.0)
    result = runtime.tick()
    assert result.physiology is not None and result.physiology.state.value == "dead"
    assert authority.live_ids == ("parent",)
    assert authority.observe_death(runtime) is not None
    assert authority.observe_death(runtime) is None
    assert authority.live_ids == ()
    try:
        runtime.tick()
    except OrganismDeadError:
        pass
    else:
        raise AssertionError("dead runtime must reject further ticks")
