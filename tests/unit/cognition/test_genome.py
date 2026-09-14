from __future__ import annotations

import copy

import pytest

from symbiont.cognition.genome import (
    GenomeCodec,
    GenomeError,
    parse_kernel_compatibility,
    satisfies_kernel_compatibility,
)
from symbiont.cognition.limits import KernelLimits

VALID_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_018f0000000000000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 4,
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "consolidation_interval_ticks": 32,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.02, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.92,
    },
    "structure": {
        "grow_threshold": 0.18,
        "prune_threshold": 0.01,
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


def test_master_doc_example_loads_successfully():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    assert genome.genome_id == "genome_018f0000000000000000000000"
    assert genome.development.soft_node_budget == 64
    assert genome.plasticity.learning_rate.initial == 0.02


@pytest.mark.parametrize("missing_key", list(VALID_PAYLOAD.keys()))
def test_load_rejects_missing_top_level_key(missing_key):
    payload = copy.deepcopy(VALID_PAYLOAD)
    del payload[missing_key]
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_unknown_top_level_key():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["extra_field"] = "not allowed"
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


@pytest.mark.parametrize(
    "bad_id",
    ["", "not_prefixed", "genome_/etc/passwd", "genome_" + "x" * 65, "genome_has space"],
)
def test_load_rejects_malformed_genome_id(bad_id):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["genome_id"] = bad_id
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_too_many_parent_ids():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["parent_ids"] = [f"genome_parent{i:02d}" for i in range(9)]
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_accepts_parent_ids_at_the_cap():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["parent_ids"] = [f"genome_parent{i:02d}" for i in range(8)]
    genome = GenomeCodec().load(payload)
    assert len(genome.parent_ids) == 8


@pytest.mark.parametrize(
    "bad_compat",
    ["", "not a version spec", ">=abc", "1.2.3", ">=0.55;<0.60", "eval(1)"],
)
def test_load_rejects_malformed_kernel_compatibility(bad_compat):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["kernel_compatibility"] = bad_compat
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_parse_kernel_compatibility_accepts_multi_clause_spec():
    clauses = parse_kernel_compatibility(">=0.55,<0.60")
    assert clauses == ((">=", (0, 55, 0)), ("<", (0, 60, 0)))


def test_load_rejects_range_spec_with_initial_outside_bounds():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["plasticity"]["learning_rate"] = {"initial": 0.5, "min": 0.001, "max": 0.08}
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("initial_concepts", -1),
        ("soft_node_budget", 0),
        ("soft_edge_budget", 0),
        ("consolidation_interval_ticks", 0),
    ],
)
def test_load_rejects_invalid_development_fields(field, value):
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"][field] = value
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_continuous_sigma_above_one():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["mutation_policy"]["continuous_sigma"] = 1.5
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_load_rejects_wrong_json_type():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_node_budget"] = "sixty-four"
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_genome_hash_is_deterministic_and_key_order_independent():
    genome_a = GenomeCodec().load(VALID_PAYLOAD)
    reordered = dict(reversed(list(VALID_PAYLOAD.items())))
    genome_b = GenomeCodec().load(reordered)
    assert genome_a.genome_hash == genome_b.genome_hash


def test_genome_hash_changes_when_content_changes():
    genome_a = GenomeCodec().load(VALID_PAYLOAD)
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["plasticity"]["eligibility_decay"] = 0.5
    genome_b = GenomeCodec().load(payload)
    assert genome_a.genome_hash != genome_b.genome_hash


# --- validate() against KernelLimits and running kernel version ---


def test_satisfies_kernel_compatibility_true_within_range():
    assert satisfies_kernel_compatibility(">=0.55,<0.60", (0, 57, 2))


def test_satisfies_kernel_compatibility_false_outside_range():
    assert not satisfies_kernel_compatibility(">=0.55,<0.60", (0, 60, 0))
    assert not satisfies_kernel_compatibility(">=0.55,<0.60", (0, 54, 9))


def test_validate_passes_a_genome_within_all_kernel_limits():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    GenomeCodec().validate(genome, KernelLimits(), running_version=(0, 55, 0))


def test_validate_rejects_soft_node_budget_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_node_budget"] = 999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_nodes=128), running_version=(0, 55, 0))


def test_validate_rejects_soft_edge_budget_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["soft_edge_budget"] = 9999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_edges=1024), running_version=(0, 55, 0))


def test_validate_rejects_initial_concepts_exceeding_kernel_max():
    payload = copy.deepcopy(VALID_PAYLOAD)
    payload["development"]["initial_concepts"] = 999
    genome = GenomeCodec().load(payload)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(max_concepts=32), running_version=(0, 55, 0))


def test_validate_rejects_a_running_version_outside_kernel_compatibility():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    with pytest.raises(GenomeError):
        GenomeCodec().validate(genome, KernelLimits(), running_version=(0, 60, 0))
