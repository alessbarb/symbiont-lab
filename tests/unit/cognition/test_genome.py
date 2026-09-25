from __future__ import annotations

import copy

import pytest

from symbiont.genetics.genome import GenomeCodec, GenomeError
from symbiont.genetics.genome import parse_kernel_compatibility, satisfies_kernel_compatibility
from symbiont.cognition.limits import KernelLimits


VALID_PAYLOAD = {
    "schema_version": 2,
    "genome_id": "genome_test_v2",
    "kernel_compatibility": ">=0.80,<0.90",
    "development": {
        "soft_node_budget": 192,
        "soft_edge_budget": 1536,
        "sense_node_budget": 128,
        "capacity_growth_sensitivity": 0.5,
        "consolidation_interval_ticks": 32,
    },
    "plasticity": {
        "learning_rate": {"baseline": 0.02, "min": 0.001, "max": 0.08, "adaptation_rate": 0.002},
        "eligibility_decay": 0.92,
        "structural_plasticity": {"baseline": 0.5, "min": 0.05, "max": 1.0, "adaptation_rate": 0.01},
    },
    "regulation": {
        "uncertainty_gain": 0.5,
        "novelty_gain": 0.4,
        "prediction_error_gain": 0.5,
        "controllability_loss_gain": 0.5,
        "embodiment_mismatch_gain": 0.7,
        "regulation_smoothing": 0.1,
        "regulation_decay": 0.02,
    },
    "sensorimotor": {
        "spontaneous_activity_baseline": 0.1,
        "uncertainty_exploration_gain": 0.5,
        "prediction_error_exploration_gain": 0.5,
        "exploration_habituation": 0.01,
        "reacclimation_sensitivity": 0.7,
    },
    "structure": {
        "growth_threshold": {"baseline": 0.18, "min": 0.02, "max": 0.58, "adaptation_rate": 0.01},
        "pruning_threshold": {"baseline": 0.01, "min": 0.0, "max": 0.21, "adaptation_rate": 0.005},
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "evolvability": {
        "development_mutation_scale": 0.05,
        "plasticity_mutation_scale": 0.05,
        "regulation_mutation_scale": 0.05,
        "sensorimotor_mutation_scale": 0.05,
        "structure_mutation_scale": 0.05,
        "recombination_linkage": 0.5,
    },
}


def load(payload: dict = VALID_PAYLOAD):
    return GenomeCodec().load(payload)


def test_v2_payload_loads_without_retired_genome_fields():
    genome = load()
    assert genome.schema_version == 2
    assert genome.genome_id == "genome_test_v2"
    assert genome.development.sense_node_budget == 128
    assert genome.plasticity.learning_rate.baseline == pytest.approx(0.02)
    assert not hasattr(genome, "parent_ids")
    assert not hasattr(genome, "loci_values")


@pytest.mark.parametrize("missing", VALID_PAYLOAD)
def test_load_rejects_missing_top_level_key(missing):
    payload = copy.deepcopy(VALID_PAYLOAD)
    del payload[missing]
    with pytest.raises(GenomeError):
        load(payload)


def test_load_rejects_unknown_top_level_key():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["parent_ids"] = []
    with pytest.raises(GenomeError):
        load(payload)


@pytest.mark.parametrize("bad_id", ["", "not_prefixed", "genome_/etc", "genome_has space"])
def test_load_rejects_malformed_genome_id(bad_id):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["genome_id"] = bad_id
    with pytest.raises(GenomeError):
        load(payload)


@pytest.mark.parametrize("field,value", [
    ("soft_node_budget", 0),
    ("soft_edge_budget", 0),
    ("sense_node_budget", 0),
    ("consolidation_interval_ticks", 0),
])
def test_load_rejects_invalid_development_fields(field, value):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"][field] = value
    with pytest.raises(GenomeError):
        load(payload)


def test_load_rejects_sensory_budget_above_node_budget():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["sense_node_budget"] = 193
    with pytest.raises(GenomeError):
        load(payload)


def test_load_rejects_wrong_json_type_as_genome_error():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_node_budget"] = "192"
    with pytest.raises(GenomeError):
        load(payload)


def test_load_rejects_removed_v1_schema():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["schema_version"] = 1
    with pytest.raises(GenomeError):
        load(payload)


@pytest.mark.parametrize("bad_compatibility", ["", ">=abc", "1.2.3", ">=0.80;<0.90"])
def test_load_rejects_malformed_kernel_compatibility(bad_compatibility):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["kernel_compatibility"] = bad_compatibility
    with pytest.raises(GenomeError):
        load(payload)


def test_hash_is_key_order_independent_and_changes_with_content():
    first = load()
    reordered = dict(reversed(list(VALID_PAYLOAD.items())))
    assert first.genome_hash == load(reordered).genome_hash
    changed = copy.deepcopy(VALID_PAYLOAD)
    changed["plasticity"]["eligibility_decay"] = 0.5
    assert first.genome_hash != load(changed).genome_hash


def test_kernel_compatibility_parser_and_predicate():
    assert parse_kernel_compatibility(">=0.80,<0.90") == ((">=", (0, 80, 0)), ("<", (0, 90, 0)))
    assert satisfies_kernel_compatibility(">=0.80,<0.90", (0, 85, 0))
    assert not satisfies_kernel_compatibility(">=0.80,<0.90", (0, 79, 9))
    assert not satisfies_kernel_compatibility(">=0.80,<0.90", (0, 90, 0))


def test_validate_accepts_current_kernel_version_and_limits():
    GenomeCodec().validate(load(), KernelLimits(), running_version=(0, 85, 0))


@pytest.mark.parametrize("running_version", [(0, 79, 9), (0, 90, 0)])
def test_validate_rejects_kernel_version_outside_declared_range(running_version):
    with pytest.raises(GenomeError):
        GenomeCodec().validate(load(), KernelLimits(), running_version=running_version)


def test_validate_rejects_kernel_limit_overflow():
    with pytest.raises(GenomeError):
        GenomeCodec().validate(load(), KernelLimits(max_nodes=64), running_version=(0, 85, 0))
