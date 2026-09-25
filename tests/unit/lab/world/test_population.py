import pytest

from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology


def _topo() -> HexTopology:
    return HexTopology(width=8, height=8)


def test_founder_placement_is_deterministic_for_the_same_seed():
    a = founder_placement(101, _topo(), 8)
    b = founder_placement(101, _topo(), 8)
    assert a == b


def test_founder_placement_produces_distinct_cells():
    cells = founder_placement(101, _topo(), 8)
    assert len(set(cells)) == 8


def test_founder_placement_different_seeds_diverge():
    a = founder_placement(101, _topo(), 8)
    b = founder_placement(127, _topo(), 8)
    assert a != b


def test_founder_placement_rejects_count_exceeding_topology():
    tiny = HexTopology(width=2, height=2)
    with pytest.raises(ValueError):
        founder_placement(101, tiny, 5)


def _population(seed: int = 101, count: int = 8) -> PopulationGenesisRuntime:
    topo = _topo()
    cells = founder_placement(seed, topo, count)
    return PopulationGenesisRuntime(
        organism_ids=tuple(f"org-{i}" for i in range(count)),
        world_seed=seed,
        ground_truth=build_ground_truth(),
        topology=topo,
        start_cells=cells,
    )


def test_population_occupies_distinct_cells_no_collision():
    pop = _population()
    occupied = pop.state.occupancy.snapshot()
    assert len(occupied) == 8
    assert len(set(occupied)) == 8


def test_population_rejects_duplicate_organism_ids():
    topo = _topo()
    cells = founder_placement(101, topo, 2)
    with pytest.raises(ValueError):
        PopulationGenesisRuntime(
            organism_ids=("org-a", "org-a"),
            world_seed=101,
            ground_truth=build_ground_truth(),
            topology=topo,
            start_cells=cells,
        )


def test_population_runs_many_ticks_without_raising():
    pop = _population()
    records = pop.run(30)
    assert len(records) == 30
    assert pop.state.tick == 30


def test_population_tick_order_is_by_sorted_organism_id():
    pop = _population(count=3)
    assert pop.organism_ids == ("org-0", "org-1", "org-2")


def test_no_organism_moves_in_v2_scope():
    pop = _population()
    start = {oid: pop.state.bodies[oid].occupied_cell for oid in pop.organism_ids}
    pop.run(30)
    for oid in pop.organism_ids:
        assert pop.state.bodies[oid].occupied_cell == start[oid]


def test_population_is_deterministic_for_same_seed():
    a = _population(seed=101)
    b = _population(seed=101)
    records_a = a.run(20)
    records_b = b.run(20)
    actions_a = [
        {oid: r.action.action_id for oid, r in rec.per_organism.items()} for rec in records_a
    ]
    actions_b = [
        {oid: r.action.action_id for oid, r in rec.per_organism.items()} for rec in records_b
    ]
    assert actions_a == actions_b


def test_dead_organisms_are_skipped_not_crashed_on():
    pop = _population(count=2)
    pop.run(5)
    # Force one organism dead directly and confirm the population keeps going.
    victim = pop.organism_ids[0]
    pop._rigs[victim].runtime._living_body_state.mark_dead(pop.state.tick)
    records = pop.run(5)
    assert len(records) == 5
    for record in records:
        assert victim not in record.per_organism
