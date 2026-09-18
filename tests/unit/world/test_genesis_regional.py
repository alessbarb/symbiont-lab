import pytest

from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.laws import HazardLaw, ResourceLaw
from symbiont_world.topology import HexCoord

RESOURCE_ID = "r7c2e9a1b4d80556"
HAZARD_ID = "h9f3d1c8a2e60734"
REGION_A = "region-a-hash"
REGION_B = "region-b-hash"


def _split_region(cell: HexCoord) -> str:
    return REGION_A if cell.q < 4 else REGION_B


def _ground_truth() -> GroundTruth:
    base_resource = ResourceLaw(capacity=10.0, renewal_rate=0.1, decay_rate=0.0, initial_quantity=5.0)
    base_hazard = HazardLaw(base_probability=0.1, density_coupling=0.0)
    return GroundTruth(
        resources={RESOURCE_ID: base_resource},
        hazards={HAZARD_ID: base_hazard},
        region_of=_split_region,
        regional_resources={
            REGION_A: {RESOURCE_ID: ResourceLaw(capacity=20.0, renewal_rate=0.1, decay_rate=0.0, initial_quantity=20.0)},
        },
        regional_hazards={
            REGION_B: {HAZARD_ID: HazardLaw(base_probability=0.9, density_coupling=0.0)},
        },
    )


def test_region_without_override_falls_back_to_base_law():
    truth = _ground_truth()
    cell_in_b = HexCoord(5, 0)  # region B has no resource override
    assert truth.resource_law(cell_in_b, RESOURCE_ID).initial_quantity == 5.0


def test_region_with_override_uses_regional_law():
    truth = _ground_truth()
    cell_in_a = HexCoord(1, 0)
    assert truth.resource_law(cell_in_a, RESOURCE_ID).initial_quantity == 20.0


def test_hazard_regional_override():
    truth = _ground_truth()
    cell_in_b = HexCoord(5, 0)
    cell_in_a = HexCoord(1, 0)
    assert truth.hazard_law(cell_in_b, HAZARD_ID).base_probability == 0.9
    assert truth.hazard_law(cell_in_a, HAZARD_ID).base_probability == 0.1  # falls back


def test_ground_truth_without_regions_behaves_exactly_like_v1():
    truth = GroundTruth(resources={RESOURCE_ID: ResourceLaw(capacity=10.0, renewal_rate=0.0, decay_rate=0.0, initial_quantity=3.0)})
    assert truth.region_of_cell(HexCoord(0, 0)) is None
    assert truth.resource_law(HexCoord(0, 0), RESOURCE_ID).initial_quantity == 3.0


def test_environment_resource_pool_uses_regional_law_lazily():
    env = WorldEnvironment(_ground_truth())
    pool_a = env.resource_pool(HexCoord(1, 0))
    pool_b = env.resource_pool(HexCoord(5, 0))
    assert pool_a[RESOURCE_ID] == 20.0
    assert pool_b[RESOURCE_ID] == 5.0


def test_environment_hazard_exposures_at_uses_region():
    env = WorldEnvironment(_ground_truth())
    exposures_a = env.hazard_exposures_at(HexCoord(1, 0), local_density=0.0)
    exposures_b = env.hazard_exposures_at(HexCoord(5, 0), local_density=0.0)
    assert exposures_a[HAZARD_ID] == pytest.approx(0.1)
    assert exposures_b[HAZARD_ID] == pytest.approx(0.9)


def test_legacy_hazard_exposures_ignores_region_for_backward_compatibility():
    env = WorldEnvironment(_ground_truth())
    exposures = env.hazard_exposures(local_density=0.0)
    assert exposures[HAZARD_ID] == pytest.approx(0.1)


def test_regional_maps_are_immutable():
    truth = _ground_truth()
    with pytest.raises(TypeError):
        truth.regional_resources[REGION_A][RESOURCE_ID] = None
