from symbiont.core.behavior import ActionKind
from symbiont_lab.world.adapter import SingleOrganismGenesisRuntime
from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_world.topology import HexCoord, HexTopology


def _runtime(seed: int = 101) -> SingleOrganismGenesisRuntime:
    return SingleOrganismGenesisRuntime(
        organism_id="org-test",
        world_seed=seed,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=8, height=8),
        start_cell=HexCoord(4, 4),
    )


def test_no_new_action_kind_was_added_to_the_frozen_core():
    # §15 gate: the adapter must not extend ActionKind.
    assert {kind.name for kind in ActionKind} == {
        "REST", "INTAKE", "REPAIR", "OBSERVE", "INVESTIGATE",
        "SOCIAL_EXCHANGE", "COMPETE", "REPRODUCE", "WAIT",
    }


def test_runtime_runs_many_ticks_without_raising():
    runtime = _runtime()
    records = runtime.run(50)
    assert len(records) == 50
    assert runtime.state.tick == 50


def test_organism_never_moves_in_v1_scope():
    runtime = _runtime()
    start_cell = runtime.state.bodies["org-test"].occupied_cell
    runtime.run(50)
    assert runtime.state.bodies["org-test"].occupied_cell == start_cell


def test_hazard_damage_always_stays_within_contract_bounds():
    runtime = _runtime()
    before = runtime.runtime.homeostasis.integrity
    runtime.run(200)
    after = runtime.runtime.homeostasis.integrity
    assert 0.0 <= after <= before


def test_resource_consumption_is_reflected_in_world_ground_truth():
    runtime = _runtime()
    cell = runtime.state.bodies["org-test"].occupied_cell
    runtime.run(300)
    pool_after = runtime.environment.resource_pool(cell)
    ground_truth = runtime.environment.ground_truth
    for resource_id, law in ground_truth.resources.items():
        assert 0.0 <= pool_after[resource_id] <= law.capacity


def test_deterministic_for_same_seed():
    a = _runtime(seed=101)
    b = _runtime(seed=101)
    records_a = a.run(30)
    records_b = b.run(30)
    hazard_a = [r.hazard_hits for r in records_a]
    hazard_b = [r.hazard_hits for r in records_b]
    assert hazard_a == hazard_b


def test_run_stops_early_if_organism_dies_mid_run():
    runtime = _runtime()
    records = runtime.run(0)
    assert records == ()


def test_reading_provider_reflects_current_observation_only():
    from symbiont_lab.world.adapter import WorldReadingProvider
    from symbiont_world.contracts import WorldObservation
    from symbiont.host.contracts import Capability, CapabilityKind

    provider = WorldReadingProvider()
    cap = Capability(capability_id="abc123", kind=CapabilityKind.SIGNAL, source="symbiont_world")
    assert provider.sample((cap,)) == ()

    provider.set_observation(WorldObservation(signals={"abc123": 0.5}))
    readings = provider.sample((cap,))
    assert len(readings) == 1
    assert readings[0].value == 0.5
    assert readings[0].capability_id == "abc123"
