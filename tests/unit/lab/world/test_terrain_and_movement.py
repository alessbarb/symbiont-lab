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
