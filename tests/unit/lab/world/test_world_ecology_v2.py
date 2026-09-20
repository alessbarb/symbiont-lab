from __future__ import annotations

import pytest

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



def test_physiology_balance_closes_energy_and_integrity_identities():
    pop = _clean_population(seed=101, count=1, width=3, height=2)
    pop.run_tick()

    events = [
        event
        for event in pop.journal
        if event.kind == "PHYSIOLOGY_BALANCE"
    ]
    assert len(events) == 1
    payload = events[0].payload

    assert payload["energy_end"] == pytest.approx(
        payload["energy_start"]
        + payload["absorbed"]
        - payload["motor_cost"]
        - payload["basal_cost"],
        abs=1e-12,
    )
    assert payload["integrity_end"] == pytest.approx(
        payload["integrity_start"]
        - payload["basal_wear"]
        - payload["deferred_damage"]
        - payload["hazard_damage"],
        abs=1e-12,
    )


def test_death_event_reports_physical_terminal_cause():
    pop = _clean_population(seed=101, count=1, width=3, height=2)
    oid = pop.organism_ids[0]
    body = pop._rigs[oid].individual.body
    body.physiology.energy_reserve = 1e-6

    pop.run_tick()

    deaths = [event for event in pop.journal if event.kind == "DEATH"]
    assert len(deaths) == 1
    assert deaths[0].payload["cause"] == "energy_depletion"



def test_resource_renewal_telemetry_is_one_aggregate_event_per_tick():
    pop = _clean_population(seed=101, count=3, width=3, height=2)
    pop.run_tick()

    renewal_events = [
        event for event in pop.journal if event.kind == "RESOURCE_RENEWED"
    ]
    assert len(renewal_events) == 1
    event = renewal_events[0]
    assert event.actor is None
    assert event.position is None
    assert event.payload["cell_count"] == 6
    assert 0.0 <= event.payload["min_renewal_factor"] <= event.payload["max_renewal_factor"]
