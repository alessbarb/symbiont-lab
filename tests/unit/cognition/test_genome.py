from __future__ import annotations

import copy

import pytest

from symbiont.cognition.genome import GenomeCodec, GenomeError, parse_kernel_compatibility

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
