"""Unit tests for DynamicGeography, rich CellPhenotype, and spatial movement (Phase P0)."""
import pytest

from symbiont_world.genesis import GroundTruth
from symbiont_world.state import TickAborted
from symbiont_world.topology import HexCoord, HexTopology
from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.persistence import (
    capture_checkpoint,
    restore_population_from_checkpoint,
)
from symbiont_lab.world.population import PopulationGenesisRuntime
from symbiont_lab.world.terrain import CellPhenotype, DynamicGeography


def test_dynamic_geography_determinism():
    topo = HexTopology(width=8, height=8)
    geo1 = DynamicGeography(topo, world_seed=42)
    geo2 = DynamicGeography(topo, world_seed=42)

    for q in range(8):
        for r in range(8):
            c = HexCoord(q, r)
            assert geo1.elevation(c) == geo2.elevation(c)
            assert geo1.permeability(c) == geo2.permeability(c)
            assert geo1.moisture(c) == geo2.moisture(c)
            assert geo1.temperature(c) == geo2.temperature(c)
            assert geo1.fertility(c) == geo2.fertility(c)


def test_dynamic_geography_bounds():
    topo = HexTopology(width=16, height=16)
    geo = DynamicGeography(topo, world_seed=101)

    for q in range(16):
        for r in range(16):
            c = HexCoord(q, r)
            assert 0.0 <= geo.elevation(c) <= 1.0
            assert 0.0 <= geo.permeability(c) <= 1.0
            assert 0.0 <= geo.moisture(c) <= 1.0
            assert 0.0 <= geo.temperature(c) <= 1.0
            assert 0.0 <= geo.fertility(c) <= 1.0


def test_traversal_respects_boundaries_and_cliffs():
    topo = HexTopology(width=6, height=6)
    geo = DynamicGeography(topo, world_seed=101)

    # In-bounds traversals
    c1 = HexCoord(0, 0)
    c2 = HexCoord(1, 0)
    can_t = geo.can_traverse(c1, c2)
    assert isinstance(can_t, bool)

    # Out of bounds should always fail
    out_of_bounds = HexCoord(-1, 0)
    assert geo.can_traverse(c1, out_of_bounds) is False


def test_traces_deposit_and_decay():
    topo = HexTopology(width=6, height=6)
    geo = DynamicGeography(topo, world_seed=101)
    cell = HexCoord(2, 2)

    assert geo.traces(cell) == 0.0
    geo.deposit_trace(cell, 0.5)
    assert geo.traces(cell) == 0.5

    # Advance steps with no occupants
    geo.step([])
    assert geo.traces(cell) < 0.5
    assert geo.traces(cell) > 0.0


def test_spatial_movement_when_enabled():
    topo = HexTopology(width=6, height=6)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a", "org-b"),
        world_seed=202,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(1, 1), HexCoord(4, 4)),
        movement_enabled=True,
    )

    initial_pos = {oid: pop.state.bodies[oid].occupied_cell for oid in pop.organism_ids}

    # Run for 25 ticks
    records = pop.run(25)
    assert len(records) == 25

    # At least one MOVE event should be recorded in the journal across 25 ticks
    move_events = [e for e in pop.journal.replay() if e.kind == "MOVE"]
    assert len(move_events) > 0

    # Traces should have been deposited along the path
    has_any_trace = any(
        pop.geography.traces(HexCoord(q, r)) > 0
        for q in range(topo.width)
        for r in range(topo.height)
    )
    assert has_any_trace is True


def test_geography_rollback_on_failed_tick():
    topo = HexTopology(width=6, height=6)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=303,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(2, 2),),
        movement_enabled=True,
    )

    # Step once normally
    pop.run_tick()
    traces_before = pop.geography.snapshot()

    # Simulate a forced tick failure
    from symbiont_lab.world.transaction import IntegratedWorldTickTransaction
    tx = IntegratedWorldTickTransaction(
        state=pop.state,
        environment=pop.environment,
        rigs=pop._rigs,
        deferred_queue=pop.deferred_queue,
        journal=pop.journal,
        geography=pop.geography,
    )
    with tx:
        pop.geography.deposit_trace(HexCoord(0, 0), 0.99)
        raise TickAborted("forced failure test")

    # Assert transaction rolled back and geography was restored exactly
    assert tx.committed is False
    assert pop.geography.snapshot() == traces_before
    assert pop.geography.traces(HexCoord(0, 0)) == 0.0


def test_geography_checkpoint_and_restore_equivalence():
    topo = HexTopology(width=6, height=6)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a", "org-b"),
        world_seed=404,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(1, 1), HexCoord(3, 3)),
        movement_enabled=True,
    )

    pop.run(15)
    chk = capture_checkpoint(pop, world_fingerprint="fp-test")
    assert chk.geography is not None
    assert "elevation" in chk.geography
    assert "traces" in chk.geography

    restored = restore_population_from_checkpoint(chk, gt)
    assert restored.geography is not None
    assert restored.geography.traces(HexCoord(1, 1)) == pop.geography.traces(HexCoord(1, 1))
    assert restored.geography.elevation(HexCoord(2, 2)) == pop.geography.elevation(HexCoord(2, 2))
    assert restored.geography.snapshot()["surface_water"] == pop.geography.snapshot()["surface_water"]
    assert restored.geography.snapshot()["detritus"] == pop.geography.snapshot()["detritus"]
    assert restored.geography.snapshot()["ecological_pressure"] == pop.geography.snapshot()["ecological_pressure"]



def test_dynamic_ecology_death_deposits_detritus_and_changes_fertility():
    from symbiont_lab.world.terrain import DynamicGeography
    from symbiont_world.topology import HexCoord, HexTopology

    topo = HexTopology(width=4, height=4)
    geo = DynamicGeography(topo, 123)
    cell = HexCoord(1, 1)
    before = geo.effective_fertility(cell)

    geo.step((), death_cells=(cell,))

    assert geo.detritus(cell) > 0.0
    assert geo.disturbance(cell) > 0.0
    assert geo.effective_fertility(cell) != pytest.approx(before)


def test_dynamic_ecology_presence_creates_pressure_and_then_decays():
    from symbiont_lab.world.terrain import DynamicGeography
    from symbiont_world.topology import HexCoord, HexTopology

    topo = HexTopology(width=4, height=4)
    geo = DynamicGeography(topo, 321)
    cell = HexCoord(2, 2)

    geo.step((cell,))
    pressure_after_presence = geo.ecological_pressure(cell)
    assert pressure_after_presence > 0.0

    geo.step(())
    assert geo.ecological_pressure(cell) < pressure_after_presence


def test_surface_water_is_deterministic_and_persistent_roundtrip():
    from symbiont_lab.world.terrain import DynamicGeography
    from symbiont_world.topology import HexTopology

    topo = HexTopology(width=6, height=6)
    a = DynamicGeography(topo, 909)
    b = DynamicGeography(topo, 909)

    assert a.snapshot()["surface_water"] == b.snapshot()["surface_water"]

    restored = DynamicGeography.from_dict(a.to_dict())
    assert restored.snapshot() == a.snapshot()


def test_ecological_pressure_reduces_resource_renewal_factor():
    from symbiont_lab.world.terrain import DynamicGeography
    from symbiont_world.topology import HexCoord, HexTopology

    topo = HexTopology(width=3, height=3)
    geo = DynamicGeography(topo, 515)
    cell = HexCoord(1, 1)
    baseline = geo.resource_renewal_factor(cell)

    for _ in range(8):
        geo.step((cell,))

    assert geo.resource_renewal_factor(cell) < baseline



def test_directional_impulse_redistributes_existing_substrate_without_semantic_action():
    topo = HexTopology(width=4, height=4)
    geo = DynamicGeography(topo, 707)
    origin = HexCoord(1, 1)
    target = origin.neighbor(0)

    geo._surface_water[origin] = 0.6
    geo._detritus[origin] = 0.5
    before_water = geo.surface_water(origin)
    before_detritus = geo.detritus(origin)

    result = geo.apply_directional_impulse(origin, target, 1.0)

    assert result.water_transferred > 0.0
    assert result.detritus_transferred > 0.0
    assert geo.surface_water(origin) < before_water
    assert geo.detritus(origin) < before_detritus
    assert geo.surface_water(target) > 0.0
    assert geo.detritus(target) > 0.0
    assert geo.disturbance(origin) > 0.0
    assert geo.disturbance(target) > 0.0


def test_boundary_impulse_disturbs_origin_without_fabricating_transfer():
    topo = HexTopology(width=2, height=2)
    geo = DynamicGeography(topo, 808)
    origin = HexCoord(0, 0)

    result = geo.apply_directional_impulse(origin, origin, 0.8)

    assert result.water_transferred == 0.0
    assert result.detritus_transferred == 0.0
    assert geo.disturbance(origin) > 0.0


def test_substrate_impulse_is_transactionally_rolled_back():
    topo = HexTopology(width=3, height=3)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=919,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
    )
    origin = HexCoord(1, 1)
    target = origin.neighbor(0)
    pop.geography._surface_water[origin] = 0.5
    before = pop.geography.snapshot()

    from symbiont_lab.world.transaction import IntegratedWorldTickTransaction
    tx = IntegratedWorldTickTransaction(
        state=pop.state,
        environment=pop.environment,
        rigs=pop._rigs,
        deferred_queue=pop.deferred_queue,
        journal=pop.journal,
        geography=pop.geography,
    )
    with tx:
        pop.geography.apply_directional_impulse(origin, target, 1.0)
        raise TickAborted("rollback impulse")

    assert pop.geography.snapshot() == before



def test_substrate_history_can_open_and_close_traversal_without_new_action_type():
    topo = HexTopology(width=3, height=3)
    origin = HexCoord(1, 1)
    target = origin.neighbor(0)
    geo = DynamicGeography(topo, 1313)
    geo._permeability[target] = 0.14
    geo._surface_water.clear()
    geo._detritus.clear()
    geo._disturbance.clear()

    assert geo.can_traverse(origin, target) is False

    for _ in range(8):
        geo.apply_directional_impulse(origin, target, 1.0)
    assert geo.effective_permeability(target) >= 0.15
    assert geo.can_traverse(origin, target) is True

    geo._detritus[target] = 1.0
    assert geo.effective_permeability(target) < 0.15
    assert geo.can_traverse(origin, target) is False


def test_population_observation_changes_after_same_opaque_motor_consequence():
    from symbiont_lab.world.adapter import local_substrate_signals

    topo = HexTopology(width=4, height=4)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=1414,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
    )
    cell = pop.state.bodies["org-a"].occupied_cell
    target = cell.neighbor(0)
    pop.geography._surface_water[cell] = 0.6
    pop.geography._detritus[cell] = 0.5

    expected_before = local_substrate_signals(pop.geography, cell)
    obs_before = pop._observation_for("org-a")
    assert all(obs_before.signals[key] == pytest.approx(value) for key, value in expected_before.items())

    pop.geography.apply_directional_impulse(cell, target, 1.0)
    expected_after = local_substrate_signals(pop.geography, cell)
    obs_after = pop._observation_for("org-a")

    assert any(expected_before[key] != expected_after[key] for key in expected_before)
    assert all(obs_after.signals[key] == pytest.approx(value) for key, value in expected_after.items())



def test_motor_actuation_commits_substrate_impulse_event_without_new_world_action():
    from symbiont.actuation.types import Actuation
    from symbiont_lab.world.transaction import IntegratedWorldTickTransaction

    topo = HexTopology(width=4, height=4)
    gt = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=1515,
        ground_truth=gt,
        topology=topo,
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
    )
    rig = pop._rigs["org-a"]
    actuator_id = rig.runtime.actuator_constitution.actuator_ids[0]
    rig.runtime._last_actuation = Actuation(
        actuator_id=actuator_id,
        requested=1.0,
        delivered=1.0,
    )

    tx = IntegratedWorldTickTransaction(
        state=pop.state,
        environment=pop.environment,
        rigs=pop._rigs,
        deferred_queue=pop.deferred_queue,
        journal=pop.journal,
        geography=pop.geography,
    )
    with tx:
        pop._resolve_spatial_movement(tx, current_tick=pop.state.tick)

    events = pop.journal.replay()
    impulse_events = [event for event in events if event.kind == "SUBSTRATE_IMPULSE"]
    assert len(impulse_events) == 1
    assert impulse_events[0].actor == "org-a"
    assert impulse_events[0].payload["actuator_id"] == actuator_id
    assert impulse_events[0].payload["delivered"] == pytest.approx(1.0)



def test_clean_population_observation_contains_no_apparatus_resource_hazard_or_occupancy_ids():
    from symbiont_lab.world.adapter import local_substrate_signals
    from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL

    truth = build_ground_truth()
    pop = PopulationGenesisRuntime(
        organism_ids=("clean-a",),
        world_seed=1616,
        ground_truth=truth,
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    observation = pop._observation_for("clean-a")
    ids = set(observation.signals)

    assert len(ids) == 8
    assert LOCAL_OCCUPANCY_SIGNAL not in ids
    assert ids.isdisjoint(set(truth.fields))
    assert ids.isdisjoint(set(truth.resources))
    assert ids.isdisjoint(set(truth.hazards))
    assert ids.isdisjoint(set(local_substrate_signals(pop.geography, HexCoord(1, 1))))


def test_clean_population_does_not_execute_typed_local_action_frontier():
    pop = PopulationGenesisRuntime(
        organism_ids=("clean-a",),
        world_seed=1717,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    record = pop.run_tick()
    assert record is not None
    action = record.per_organism["clean-a"].action
    assert action.action_id == "opaque_motor"
    assert action.action_id not in {
        "rest", "intake", "repair", "observe", "investigate",
        "social_exchange", "compete", "reproduce", "wait",
    }

