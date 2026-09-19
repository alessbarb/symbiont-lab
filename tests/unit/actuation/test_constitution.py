from __future__ import annotations

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.constitution import ActuatorConstitution, MotorSlot, derive_actuator_constitution


def test_derive_actuator_constitution_produces_slot_count_slots():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=4))
    assert len(constitution.slots) == 4
    assert all(isinstance(slot, MotorSlot) for slot in constitution.slots)


def test_actuator_ids_are_unique_and_stable_across_calls():
    motor = MotorGenes(slot_count=6)
    first = derive_actuator_constitution(motor)
    second = derive_actuator_constitution(motor)
    assert first.actuator_ids == second.actuator_ids
    assert len(set(first.actuator_ids)) == 6


def test_actuator_ids_stable_when_only_non_motor_genes_change():
    # Same MotorGenes content -> same actuator_ids, regardless of what else
    # differs elsewhere in a genome. This module only ever sees MotorGenes,
    # so it cannot see (and therefore cannot react to) unrelated mutations.
    baseline = derive_actuator_constitution(MotorGenes())
    same_motor_genes = derive_actuator_constitution(MotorGenes())
    assert baseline.actuator_ids == same_motor_genes.actuator_ids


def test_actuator_ids_change_only_when_slot_count_changes():
    six_slots = derive_actuator_constitution(MotorGenes(slot_count=6))
    three_slots = derive_actuator_constitution(MotorGenes(slot_count=3))
    assert set(three_slots.actuator_ids) <= set(six_slots.actuator_ids)


def test_slot_params_do_not_affect_actuator_id():
    cheap = derive_actuator_constitution(MotorGenes(slot_count=2, basal_cost=0.01))
    expensive = derive_actuator_constitution(MotorGenes(slot_count=2, basal_cost=0.5))
    assert cheap.actuator_ids == expensive.actuator_ids


def test_constitution_slots_are_immutable_tuple_not_dict():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    assert isinstance(constitution.slots, tuple)
    with pytest.raises(AttributeError):
        constitution.slots = ()  # type: ignore[misc]


def test_slot_for_looks_up_by_actuator_id():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    actuator_id = constitution.actuator_ids[0]
    slot = constitution.slot_for(actuator_id)
    assert slot.actuator_id == actuator_id


def test_slot_for_raises_for_unknown_actuator_id():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    with pytest.raises(KeyError):
        constitution.slot_for("actuator.does-not-exist")


from symbiont.cognition.birth import load_actuator_constitution
from symbiont.cognition.genome import Genome, GenomeCodec


def _genome_with_motor(**motor_kwargs) -> Genome:
    from tests.unit.actuation.test_genome_motor_genes import _base_payload

    payload = _base_payload()
    if motor_kwargs:
        payload["motor"] = {
            "slot_count": motor_kwargs.get("slot_count", 6),
            "basal_cost": motor_kwargs.get("basal_cost", 0.05),
            "initial_health": motor_kwargs.get("initial_health", 1.0),
            "execution_threshold": motor_kwargs.get("execution_threshold", 0.5),
        }
    return GenomeCodec().load(payload)


def test_load_actuator_constitution_from_genome_matches_direct_derivation():
    genome = _genome_with_motor(slot_count=3)
    from_birth = load_actuator_constitution(genome)
    direct = derive_actuator_constitution(genome.motor)
    assert from_birth.actuator_ids == direct.actuator_ids


def test_load_actuator_constitution_ignores_non_motor_gene_mutations():
    # Empirical version of the stability property: two genomes that differ
    # in genome_id and an unrelated gene (plasticity.learning_rate), but
    # share identical MotorGenes, must yield identical actuator_ids. This
    # is what would break if load_actuator_constitution ever salted its
    # derivation with genome_id/genome_hash instead of genome.motor alone.
    from tests.unit.actuation.test_genome_motor_genes import _base_payload

    payload_a = _base_payload()
    payload_b = _base_payload()
    payload_b["genome_id"] = "genome_test1111111111111111111111"
    payload_b["plasticity"]["learning_rate"]["initial"] = 0.42

    genome_a = GenomeCodec().load(payload_a)
    genome_b = GenomeCodec().load(payload_b)

    assert genome_a.genome_hash != genome_b.genome_hash
    assert genome_a.motor == genome_b.motor
    assert (
        load_actuator_constitution(genome_a).actuator_ids
        == load_actuator_constitution(genome_b).actuator_ids
    )
