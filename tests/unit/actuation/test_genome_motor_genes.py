from __future__ import annotations

import pytest

from symbiont.cognition.genome import Genome, GenomeCodec, GenomeError, MotorGenes


def _base_payload() -> dict:
    return {
        "schema_version": 1,
        "genome_id": "genome_test0000000000000000000000",
        "parent_ids": [],
        "kernel_compatibility": ">=0.60",
        "development": {
            "initial_concepts": 0,
            "soft_node_budget": 64,
            "soft_edge_budget": 64,
            "consolidation_interval_ticks": 10,
        },
        "plasticity": {
            "learning_rate": {"initial": 0.1, "min": 0.0, "max": 1.0},
            "forgetting_rate": {"initial": 0.05, "min": 0.0, "max": 1.0},
            "eligibility_decay": 0.9,
        },
        "structure": {
            "grow_threshold": 0.5,
            "prune_threshold": 0.1,
            "minimum_support": 2,
            "tentative_lifetime_ticks": 5,
        },
        "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 1},
    }


def test_genome_without_motor_key_gets_default_motor_genes():
    genome = GenomeCodec().load(_base_payload())
    assert genome.motor == MotorGenes()
    assert genome.motor.slot_count == 6
    assert genome.motor.basal_cost == 0.05
    assert genome.motor.initial_health == 1.0
    assert genome.motor.execution_threshold == 0.5


def test_genome_with_explicit_motor_key_round_trips():
    payload = _base_payload()
    payload["motor"] = {
        "slot_count": 3,
        "basal_cost": 0.1,
        "initial_health": 0.9,
        "execution_threshold": 0.4,
    }
    genome = GenomeCodec().load(payload)
    assert genome.motor == MotorGenes(
        slot_count=3, basal_cost=0.1, initial_health=0.9, execution_threshold=0.4
    )


def test_default_motor_genes_do_not_change_genome_hash():
    without_motor = GenomeCodec().load(_base_payload())
    payload_with_default_motor = _base_payload()
    payload_with_default_motor["motor"] = {
        "slot_count": 6,
        "basal_cost": 0.05,
        "initial_health": 1.0,
        "execution_threshold": 0.5,
    }
    with_explicit_default_motor = GenomeCodec().load(payload_with_default_motor)
    assert without_motor.genome_hash == with_explicit_default_motor.genome_hash


def test_unknown_top_level_key_still_rejected():
    payload = _base_payload()
    payload["bogus"] = {}
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_motor_slot_count_must_be_positive():
    payload = _base_payload()
    payload["motor"] = {
        "slot_count": 0,
        "basal_cost": 0.05,
        "initial_health": 1.0,
        "execution_threshold": 0.5,
    }
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)
