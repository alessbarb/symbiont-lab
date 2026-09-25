from __future__ import annotations

import pytest

from symbiont_lab.world.genesis_v1 import HAZARD_IDS, build_constitution, build_ground_truth
from symbiont_lab.world.persistence import WorldStorage
from symbiont_lab.world.population import PopulationGenesisRuntime
from symbiont_world.genesis import WorldEnvironment
from symbiont_world.topology import HexCoord, HexTopology


def test_cyclical_hazard_has_real_temporal_windows():
    truth = build_ground_truth()
    env = WorldEnvironment(truth)
    cell = HexCoord(4, 0)  # neutral apparatus-side patch
    hazard_id = HAZARD_IDS["hazard-cyclical"]

    env.propagate_fields(0)
    baseline = env.hazard_exposures_at(cell, 0.0)[hazard_id]
    env.propagate_fields(40)
    peak = env.hazard_exposures_at(cell, 0.0)[hazard_id]
    env.propagate_fields(120)
    trough = env.hazard_exposures_at(cell, 0.0)[hazard_id]

    assert baseline == pytest.approx(0.006)
    assert peak == pytest.approx(0.012)
    assert trough == pytest.approx(0.0, abs=1e-12)


def test_hazard_ecology_has_persistent_spatial_patches():
    truth = build_ground_truth()
    env = WorldEnvironment(truth)
    env.propagate_fields(40)
    hazard_id = HAZARD_IDS["hazard-cyclical"]

    sheltered = env.hazard_exposures_at(HexCoord(0, 0), 0.0)[hazard_id]
    neutral = env.hazard_exposures_at(HexCoord(4, 0), 0.0)[hazard_id]
    exposed = env.hazard_exposures_at(HexCoord(0, 4), 0.0)[hazard_id]

    assert 0.0 < sheltered < neutral < exposed


def test_density_hazard_is_low_when_isolated_and_rises_with_living_density():
    truth = build_ground_truth()
    env = WorldEnvironment(truth)
    env.propagate_fields(0)
    cell = HexCoord(4, 0)
    hazard_id = HAZARD_IDS["hazard-density-coupled"]

    isolated = env.hazard_exposures_at(cell, 0.0)[hazard_id]
    grouped = env.hazard_exposures_at(cell, 0.2)[hazard_id]

    assert isolated == pytest.approx(0.0015)
    assert grouped == pytest.approx(0.0075)
    assert grouped > isolated


def _two_founders() -> PopulationGenesisRuntime:
    topology = HexTopology(width=8, height=8)
    return PopulationGenesisRuntime(
        organism_ids=("a", "b"),
        world_seed=101,
        ground_truth=build_ground_truth(),
        topology=topology,
        start_cells=(HexCoord(2, 2), HexCoord(3, 2)),
        movement_enabled=False,
        experimental_clean=True,
    )


def test_dead_occupant_does_not_contribute_to_living_density():
    pop = _two_founders()
    assert pop._living_density("a") > 0.0

    pop._rigs["b"].individual.body.physiology.structural_integrity = 0.0

    # b is still physically present in OccupancyGrid before the tick cleanup,
    # but living density must already ignore it.
    assert pop.state.occupancy.cell_of("b") == HexCoord(3, 2)
    assert pop._living_density("a") == 0.0


def test_death_vacates_live_occupancy_but_keeps_body_placement():
    pop = _two_founders()
    pop._rigs["b"].individual.body.physiology.energy_reserve = 1e-9

    pop.run_tick()

    assert not pop.is_alive("b")
    assert pop.state.occupancy.cell_of("b") is None
    assert pop.state.bodies["b"].occupied_cell == HexCoord(3, 2)


def test_hazard_event_records_living_density_used_for_exposure():
    pop = _two_founders()
    pop.run(20)

    events = [event for event in pop.journal.replay() if event.kind == "HAZARD_EXPOSURE"]
    for event in events:
        assert "living_density" in event.payload
        assert 0.0 <= event.payload["living_density"] <= 1.0


def test_checkpoint_preserves_temporal_hazard_phase(tmp_path):
    pop = _two_founders()
    pop.run(41)
    truth = pop.ground_truth
    constitution = build_constitution(
        truth,
        dimensions=(pop.topology.width, pop.topology.height),
    )
    storage = WorldStorage(tmp_path / "hazard-clock")
    storage.save_checkpoint(
        pop,
        world_fingerprint=constitution.fingerprint(),
        constitution=constitution,
    )

    restored = storage.restore(
        truth,
        expected_constitution=constitution,
    )

    assert restored.environment._tick == pop.environment._tick
    cell = HexCoord(4, 0)
    assert restored.environment.hazard_exposures_at(cell, 0.0) == (
        pop.environment.hazard_exposures_at(cell, 0.0)
    )
