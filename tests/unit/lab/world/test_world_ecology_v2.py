from __future__ import annotations

from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology


def _clean_population(*, seed: int, count: int, width: int = 4, height: int = 3):
    topology = HexTopology(width=width, height=height)
    cells = founder_placement(seed, topology, count)
    return PopulationGenesisRuntime(
        organism_ids=tuple(f"org-{i}" for i in range(count)),
        world_seed=seed,
        ground_truth=build_ground_truth(),
        topology=topology,
        start_cells=cells,
        movement_enabled=True,
        experimental_clean=True,
    )


def test_clean_founder_rng_is_reproducible_but_not_shared_between_individuals():
    a = _clean_population(seed=101, count=3)
    b = _clean_population(seed=101, count=3)

    states_a = {
        oid: a._rigs[oid].individual.symbiont._rng.getstate()
        for oid in a.organism_ids
    }
    states_b = {
        oid: b._rigs[oid].individual.symbiont._rng.getstate()
        for oid in b.organism_ids
    }

    assert states_a == states_b
    assert len({repr(state) for state in states_a.values()}) == len(states_a)


def test_clean_founders_do_not_emit_identical_exploration_sequences_from_rng_symmetry():
    pop = _clean_population(seed=101, count=3)

    traces = {}
    for oid in pop.organism_ids:
        sym = pop._rigs[oid].individual.symbiont
        traces[oid] = tuple(sym._rng.random() for _ in range(8))

    assert len(set(traces.values())) == len(traces)


def test_resource_renewal_runs_once_per_world_cell_per_tick_independent_of_population_size(monkeypatch):
    one = _clean_population(seed=101, count=1, width=3, height=2)
    three = _clean_population(seed=101, count=3, width=3, height=2)

    calls_one = []
    calls_three = []

    original_one = one.environment.renew_resources
    original_three = three.environment.renew_resources

    def tracked_one(cell, *, renewal_factor=1.0):
        calls_one.append(cell)
        return original_one(cell, renewal_factor=renewal_factor)

    def tracked_three(cell, *, renewal_factor=1.0):
        calls_three.append(cell)
        return original_three(cell, renewal_factor=renewal_factor)

    monkeypatch.setattr(one.environment, "renew_resources", tracked_one)
    monkeypatch.setattr(three.environment, "renew_resources", tracked_three)

    one.run_tick()
    three.run_tick()

    expected = one.topology.width * one.topology.height
    assert len(calls_one) == expected
    assert len(calls_three) == expected
    assert set(calls_one) == set(calls_three)
    assert len(set(calls_one)) == expected
    assert len(set(calls_three)) == expected
