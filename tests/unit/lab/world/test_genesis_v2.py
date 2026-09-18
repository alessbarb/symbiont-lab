from symbiont_lab.world.genesis_v1 import RESOURCE_IDS, build_ground_truth
from symbiont_lab.world.genesis_v2 import REGION_NORTH, REGION_SOUTH, build_ground_truth_v2, region_of
from symbiont_world.topology import HexCoord


def test_v2_preset_keeps_v1_field_resource_hazard_counts():
    truth = build_ground_truth_v2()
    assert len(truth.fields) == 4
    assert len(truth.resources) == 4
    assert len(truth.hazards) == 2


def test_v2_preset_uses_the_same_opaque_ids_as_v1():
    v1_truth = build_ground_truth()
    v2_truth = build_ground_truth_v2()
    assert set(v1_truth.resources) == set(v2_truth.resources)
    assert set(v1_truth.hazards) == set(v2_truth.hazards)


def test_region_of_splits_the_map_at_q_four():
    assert region_of(HexCoord(0, 0)) == REGION_NORTH
    assert region_of(HexCoord(3, 5)) == REGION_NORTH
    assert region_of(HexCoord(4, 0)) == REGION_SOUTH
    assert region_of(HexCoord(7, 7)) == REGION_SOUTH


def test_regional_override_only_touches_two_of_four_resources():
    truth = build_ground_truth_v2()
    scarce_rich = RESOURCE_IDS["resource-scarce-rich"]
    neutral = RESOURCE_IDS["resource-neutral"]

    north_cell, south_cell = HexCoord(0, 0), HexCoord(7, 0)
    # scarce-rich differs by region (overridden in north only)
    assert truth.resource_law(north_cell, scarce_rich).capacity != truth.resource_law(south_cell, scarce_rich).capacity
    # neutral has no override anywhere -- identical law in both regions
    assert truth.resource_law(north_cell, neutral).capacity == truth.resource_law(south_cell, neutral).capacity
