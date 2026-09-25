import re

import pytest

from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from symbiont_world.observation import local_observation, opaque_signal_id
from symbiont_world.topology import BodyPlacement, HexCoord, HexTopology, OccupancyGrid

_HEX_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def test_signal_id_is_opaque_hash_not_a_readable_name():
    signal_id = opaque_signal_id("local-occupancy-density")
    assert _HEX_ID_PATTERN.match(signal_id)
    assert "occupancy" not in signal_id
    assert "density" not in signal_id


def test_signal_id_is_stable_for_the_same_label():
    assert opaque_signal_id("local-occupancy-density") == opaque_signal_id(
        "local-occupancy-density"
    )


def test_local_observation_reports_zero_density_when_alone():
    topo = HexTopology(width=8, height=8)
    grid = OccupancyGrid()
    body = BodyPlacement(organism_id="org-a", occupied_cell=HexCoord(4, 4))
    grid.occupy(body.occupied_cell, "org-a")

    obs = local_observation(topo, grid, body)
    assert set(obs.signals.values()) == {0.0}


def test_local_observation_detects_occupied_neighbor():
    topo = HexTopology(width=8, height=8)
    grid = OccupancyGrid()
    center = HexCoord(4, 4)
    body = BodyPlacement(organism_id="org-a", occupied_cell=center)
    grid.occupy(center, "org-a")
    grid.occupy(center.neighbor(0), "org-b")

    obs = local_observation(topo, grid, body)
    density = next(iter(obs.signals.values()))
    assert density > 0.0


def test_local_observation_returns_no_ground_truth_field_names():
    topo = HexTopology(width=4, height=4)
    grid = OccupancyGrid()
    body = BodyPlacement(organism_id="org-a", occupied_cell=HexCoord(0, 0))
    obs = local_observation(topo, grid, body)
    for key in obs.signals:
        assert key == opaque_signal_id("local-occupancy-density")


def test_local_observation_includes_real_field_and_resource_signals_when_environment_given():
    topo = HexTopology(width=4, height=4)
    grid = OccupancyGrid()
    body = BodyPlacement(organism_id="org-a", occupied_cell=HexCoord(0, 0))
    grid.occupy(body.occupied_cell, "org-a")

    field_id, resource_id, hazard_id = "f01a4b7eb3833241", "r7c2e9a1b4d80556", "h9f3d1c8a2e60734"
    truth = GroundTruth(
        fields={field_id: PeriodicFieldLaw(amplitude=1.0, bias=0.0, angular_frequency=0.1)},
        resources={
            resource_id: ResourceLaw(
                capacity=10.0, renewal_rate=0.1, decay_rate=0.0, initial_quantity=4.0
            )
        },
        hazards={hazard_id: HazardLaw(base_probability=0.1, density_coupling=1.0)},
    )
    env = WorldEnvironment(truth)
    env.propagate_fields(tick=3)

    obs = local_observation(topo, grid, body, environment=env)
    assert obs.signals[field_id] == env.field_values()[field_id]
    assert obs.signals[resource_id] == 4.0
    assert obs.signals[hazard_id] == pytest.approx(0.1)  # alone, local density 0.0
    assert opaque_signal_id("local-occupancy-density") in obs.signals


def test_local_observation_without_environment_still_matches_w1_behavior():
    topo = HexTopology(width=4, height=4)
    grid = OccupancyGrid()
    body = BodyPlacement(organism_id="org-a", occupied_cell=HexCoord(0, 0))
    obs = local_observation(topo, grid, body)
    assert set(obs.signals) == {opaque_signal_id("local-occupancy-density")}
