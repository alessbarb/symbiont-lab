from symbiont_lab.world.genesis_v1 import (
    FIELD_IDS,
    GENESIS_V1_METADATA,
    HAZARD_IDS,
    RESOURCE_IDS,
    build_constitution,
    build_genesis_v1,
    build_ground_truth,
)


def test_genesis_v1_matches_frozen_counts():
    truth = build_ground_truth()
    assert len(truth.fields) == 4
    assert len(truth.resources) == 4
    assert len(truth.hazards) == 2


def test_ground_truth_ids_are_opaque_not_labels():
    truth = build_ground_truth()
    for opaque_id in list(truth.fields) + list(truth.resources) + list(truth.hazards):
        assert "-" not in opaque_id  # labels use hyphens; hashes never do
        assert len(opaque_id) == 16


def test_metadata_maps_labels_to_the_same_ids_ground_truth_uses():
    truth = build_ground_truth()
    assert set(GENESIS_V1_METADATA.values()) == set(truth.fields) | set(truth.resources) | set(
        truth.hazards
    )


def test_at_least_one_hazard_is_density_coupled():
    assert any(law.density_coupling > 0 for law in build_ground_truth().hazards.values())


def test_constitution_fingerprint_is_deterministic():
    a = build_constitution()
    b = build_constitution()
    assert a.fingerprint() == b.fingerprint()


def test_constitution_dimensions_match_frozen_genesis_config():
    constitution = build_constitution()
    assert constitution.world_dimensions == (64, 64)


def test_build_genesis_v1_ties_constitution_to_its_own_ground_truth():
    genesis = build_genesis_v1()
    assert (
        genesis.constitution.fingerprint() == build_constitution(genesis.ground_truth).fingerprint()
    )


def test_field_ids_are_stable_across_calls():
    assert set(FIELD_IDS.values()) == set(build_ground_truth().fields)


def test_resource_and_hazard_id_maps_are_internally_consistent():
    truth = build_ground_truth()
    assert set(RESOURCE_IDS.values()) == set(truth.resources)
    assert set(HAZARD_IDS.values()) == set(truth.hazards)
