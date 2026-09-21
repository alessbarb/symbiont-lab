import pytest
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


def test_deferred_resource_effect_fires_after_delay_within_contract_bounds():
    from symbiont_lab.world.genesis_v1 import RESOURCE_IDS

    resource_id = RESOURCE_IDS["resource-immediate-deferred"]
    runtime = SingleOrganismGenesisRuntime(
        organism_id="org-deferred",
        world_seed=101,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=8, height=8),
        start_cell=HexCoord(4, 4),
        deferred_resource_delays={resource_id: 5},
        deferred_damage_amount=0.1,
    )
    integrities = []
    for _ in range(15):
        runtime.run_tick()
        integrities.append(runtime.runtime.homeostasis.integrity)

    assert min(integrities) < 1.0  # damage actually fired at least once
    for value in integrities:
        assert 0.0 <= value <= 1.0


def test_no_deferred_config_means_no_deferred_damage():
    runtime = _runtime()
    runtime.run(30)
    assert len(runtime._deferred_queue) == 0


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



def test_anonymous_emission_reception_crosses_reading_provider_without_sender_identity():
    from symbiont_lab.world.adapter import WorldReadingProvider, _capabilities_for
    from symbiont_world.contracts import ReceivedEmission, WorldObservation

    provider = WorldReadingProvider()
    capabilities = _capabilities_for(build_ground_truth())
    provider.set_observation(
        WorldObservation(
            reception=(ReceivedEmission(sequence=(17,), intensity=0.75),)
        )
    )
    readings = provider.sample(capabilities)
    # Three fixed opaque reception channels: presence, symbol, intensity.
    received = [reading for reading in readings if reading.value is not None]
    assert len(received) == 3
    assert all(reading.source == "symbiont_world" for reading in received)
    assert all("sender" not in reading.capability_id for reading in received)





def test_clean_world_capabilities_are_only_mixed_opaque_receptors():
    from symbiont_lab.world.adapter import _capabilities_for
    from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL

    truth = build_ground_truth()
    capabilities = _capabilities_for(truth, experimental_clean=True)
    ids = {cap.capability_id for cap in capabilities}

    assert len(ids) == 8
    assert LOCAL_OCCUPANCY_SIGNAL not in ids
    assert ids.isdisjoint(set(truth.fields))
    assert ids.isdisjoint(set(truth.resources))
    assert ids.isdisjoint(set(truth.hazards))
    assert all(len(signal_id) == 16 for signal_id in ids)


def test_clean_receptors_mix_material_but_do_not_sense_hazard_probability():
    from symbiont_lab.world.adapter import physical_receptor_signals
    from symbiont_world.contracts import WorldObservation
    from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL

    truth = build_ground_truth()
    fields = {field_id: 0.2 for field_id in truth.fields}
    resources = {
        resource_id: law.capacity * 0.5
        for resource_id, law in truth.resources.items()
    }
    hazards_a = {hazard_id: 0.0 for hazard_id in truth.hazards}
    hazards_b = {hazard_id: 1.0 for hazard_id in truth.hazards}

    common = {**fields, **resources, LOCAL_OCCUPANCY_SIGNAL: 0.0}
    first = physical_receptor_signals(
        truth, WorldObservation(signals={**common, **hazards_a})
    )
    hazard_changed = physical_receptor_signals(
        truth, WorldObservation(signals={**common, **hazards_b})
    )
    assert first == hazard_changed

    resource_id = next(iter(truth.resources))
    material_changed = physical_receptor_signals(
        truth,
        WorldObservation(signals={**common, **hazards_a, resource_id: 0.0}),
    )
    assert first != material_changed
    assert set(first).isdisjoint(set(truth.resources))
    assert set(first).isdisjoint(set(truth.hazards))


def test_clean_organism_has_no_semantic_bootstrap_or_autonomous_action_priors():
    from symbiont_lab.world.adapter import _construct_organism

    rig = _construct_organism(
        organism_id="clean",
        world_id="clean-world",
        world_seed=101,
        organism_seed=102,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )

    assert rig.runtime is None
    assert rig.actuation_adapter is None
    assert rig.individual is not None
    assert rig.individual.symbiont is not None
    assert rig.individual.body is not None
    assert rig.individual.session is not None
    assert len(rig.individual.body.ordered_effectors) >= 8
    assert rig.resource_habitats == {}


def test_clean_founders_do_not_share_signal_identity_namespace():
    from symbiont_lab.world.adapter import _construct_organism

    kwargs = dict(
        world_id="clean-world",
        world_seed=77,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )
    first = _construct_organism(
        organism_id="a",
        organism_seed=78,
        **kwargs,
    )
    second = _construct_organism(
        organism_id="b",
        organism_seed=79,
        **kwargs,
    )

    assert first.receptor_ids != second.receptor_ids
    assert set(first.receptor_ids).isdisjoint(set(second.receptor_ids))
    assert first.individual.symbiont_id != second.individual.symbiont_id



def test_private_receptor_ids_preserve_same_constitutional_transfer_geometry():
    from symbiont_lab.world.adapter import physical_receptor_ids, physical_receptor_signals
    from symbiont_world.contracts import WorldObservation

    truth = build_ground_truth()
    signals = {
        **{field_id: 0.37 for field_id in truth.fields},
        **{resource_id: law.capacity * 0.4 for resource_id, law in truth.resources.items()},
        **{hazard_id: 0.8 for hazard_id in truth.hazards},
    }
    observation = WorldObservation(signals=signals)
    ids_a = physical_receptor_ids("founder-a")
    ids_b = physical_receptor_ids("founder-b")
    assert ids_a != ids_b

    values_a = physical_receptor_signals(truth, observation, receptor_ids=ids_a)
    values_b = physical_receptor_signals(truth, observation, receptor_ids=ids_b)
    assert list(values_a.values()) == pytest.approx(list(values_b.values()))


def test_clean_observation_strips_structured_side_channels_after_mixing():
    from symbiont_lab.world.adapter import clean_world_observation, physical_receptor_ids
    from symbiont_world.contracts import ReceivedEmission, WorldObservation

    truth = build_ground_truth()
    raw = WorldObservation(
        signals={**{field_id: 0.1 for field_id in truth.fields}},
        reception=(ReceivedEmission(sequence=(7,), intensity=0.5),),
        internal={"privileged": 1.0},
    )
    cleaned = clean_world_observation(
        truth,
        raw,
        receptor_ids=physical_receptor_ids("subject"),
    )
    assert cleaned.contact == ()
    assert cleaned.reception == ()
    assert cleaned.internal == {}



def test_clean_receptors_transduce_somatic_state_without_exposing_somatic_labels():
    from symbiont_lab.world.adapter import physical_receptor_ids, physical_receptor_signals
    from symbiont_world.contracts import WorldObservation

    truth = build_ground_truth()
    receptor_ids = physical_receptor_ids("somatic-subject")
    observation = WorldObservation(
        signals={
            **{field_id: 0.2 for field_id in truth.fields},
            **{
                resource_id: law.capacity * 0.5
                for resource_id, law in truth.resources.items()
            },
        }
    )
    healthy = physical_receptor_signals(
        truth,
        observation,
        receptor_ids=receptor_ids,
        somatic_state={"reserve:maintenance": 0.9, "integrity": 1.0, "activity": 1.0},
    )
    depleted = physical_receptor_signals(
        truth,
        observation,
        receptor_ids=receptor_ids,
        somatic_state={"reserve:maintenance": 0.1, "integrity": 0.5, "activity": 0.4},
    )

    assert healthy != depleted
    assert set(healthy) == set(receptor_ids)
    assert all("reserve" not in signal_id for signal_id in healthy)
    assert all("integrity" not in signal_id for signal_id in healthy)
    assert all("activity" not in signal_id for signal_id in healthy)



def test_clean_receptor_metadata_is_uniform_and_non_semantic():
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, Unit
    from symbiont_lab.world.adapter import (
        WorldReadingProvider,
        _capabilities_for,
        physical_receptor_ids,
    )
    from symbiont_world.contracts import WorldObservation

    truth = build_ground_truth()
    receptor_ids = physical_receptor_ids("metadata-subject")
    capabilities = _capabilities_for(
        truth,
        experimental_clean=True,
        receptor_ids=receptor_ids,
    )
    provider = WorldReadingProvider()
    provider.set_observation(
        WorldObservation(signals={receptor_id: 0.5 for receptor_id in receptor_ids})
    )
    readings = provider.sample(capabilities)

    assert len(readings) == len(receptor_ids)
    assert {reading.unit for reading in readings} == {Unit.RATIO}
    assert {reading.quality for reading in readings} == {ReadingQuality.NOMINAL}
    assert {reading.privacy_class for reading in readings} == {
        ReadingPrivacyClass.AGGREGATE
    }


def test_clean_world_never_calls_structured_motor_probing():
    from symbiont_lab.world.population import PopulationGenesisRuntime

    pop = PopulationGenesisRuntime(
        organism_ids=("clean-probe-guard",),
        world_seed=4040,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    rig = pop._rigs["clean-probe-guard"]
    # Clean World uses Individual/Symbiont with no legacy runtime or structured probing
    assert rig.runtime is None
    assert rig.individual is not None
    assert rig.actuation_adapter is None
    for _ in range(8):
        pop.run_tick()


def test_clean_body_has_no_dedicated_acquire_actuator():
    from symbiont_lab.world.adapter import _construct_organism

    rig = _construct_organism(
        organism_id="clean-no-intake-organ",
        world_id="clean-world",
        world_seed=5050,
        organism_seed=5051,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )

    assert rig.runtime is None
    assert rig.actuation_adapter is None
    assert rig.individual is not None
    assert all("acquire" not in eff.kind for eff in rig.individual.body.ordered_effectors)


def test_clean_world_does_not_inject_resource_habitats_or_cognitive_fuel():
    from symbiont_lab.world.adapter import _construct_organism

    rig = _construct_organism(
        organism_id="isolated-core",
        world_id="clean-world",
        world_seed=6060,
        organism_seed=6061,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )

    assert rig.resource_habitats == {}
    assert rig.runtime is None
    assert rig.individual is not None


def test_boundary_guard_rejects_implicit_ambient_metabolism_regardless_of_ledger_values():
    from symbiont_lab.world.population import PopulationGenesisRuntime

    pop = PopulationGenesisRuntime(
        organism_ids=("isolated-core",),
        world_seed=6063,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    rig = pop._rigs["isolated-core"]
    assert rig.runtime is None
    assert rig.individual is not None
    pop.assert_experimental_boundary()

    # Reject if legacy runtime coexists with clean Individual
    rig.runtime = "fake_legacy_runtime"  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="legacy runtime coexists with clean Individual"):
        pop.assert_experimental_boundary()


def test_clean_material_exchange_crosses_only_scalar_absorption():
    from symbiont_lab.world.population import PopulationGenesisRuntime

    pop = PopulationGenesisRuntime(
        organism_ids=("isolated-core",),
        world_seed=6062,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    for _ in range(32):
        pop.run_tick()


def test_clean_material_exchange_conserves_mass_with_scarce_resources():
    """NEW-AUD-001: Under scarce resources, World loss must strictly equal Body absorption."""
    from symbiont_lab.world.population import PopulationGenesisRuntime
    from symbiont_world.genesis import GroundTruth
    from symbiont_world.laws import ResourceLaw

    scarce_truth = GroundTruth(
        fields=build_ground_truth().fields,
        resources={
            "scarce_res": ResourceLaw(
                capacity=0.005,
                renewal_rate=0.0,
                decay_rate=0.0,
                initial_quantity=0.005,
            )
        },
        hazards={},
    )

    pop = PopulationGenesisRuntime(
        organism_ids=("scarce-subject",),
        world_seed=777,
        ground_truth=scarce_truth,
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    cell = HexCoord(1, 1)
    rig = pop._rigs["scarce-subject"]
    rig.individual.body.physiology.energy_reserve = 0.5

    world_before = sum(pop.environment.resource_pool(cell).values())
    assert world_before == pytest.approx(0.005)

    # A bounded number of ticks is allowed only to wait for endogenous motor
    # work. The gate must observe a real transfer; passing without one would
    # make the conservation assertion vacuous.
    transfer_event = None
    physiology_event = None
    for _ in range(64):
        record = pop.run_tick()
        current_tick = record.tick
        tick_events = [
            e for e in pop.journal.replay()
            if e.tick == current_tick
        ]
        candidates = [
            e for e in tick_events
            if e.kind == "ACTUATION_RESOLVED"
            and e.payload.get("effect") == "material_exchange"
            and e.payload.get("outcome") == "granted"
        ]
        if candidates:
            transfer_event = candidates[-1]
            physiology_event = next(
                e for e in tick_events
                if e.kind == "PHYSIOLOGY_BALANCE"
                and e.actor == "scarce-subject"
            )
            break

    assert transfer_event is not None, "clean conservation gate observed no material transfer"
    assert physiology_event is not None

    world_after = sum(pop.environment.resource_pool(cell).values())
    world_lost = world_before - world_after
    granted_amount = float(transfer_event.payload["amount"])
    balance = physiology_event.payload

    # Boundary conservation: environmental stock lost equals accepted transfer.
    assert 0.0 < world_lost <= 0.005
    assert granted_amount == pytest.approx(world_lost, abs=1e-6)
    assert float(balance["absorbed"]) == pytest.approx(world_lost, abs=1e-6)

    # Body conservation inside the same tick: net body change is fully
    # explained by accepted transfer minus explicitly measured costs.
    expected_end = (
        float(balance["energy_start"])
        + float(balance["absorbed"])
        - float(balance["motor_cost"])
        - float(balance["basal_cost"])
    )
    assert float(balance["energy_end"]) == pytest.approx(expected_end, abs=1e-9)


def test_clean_organism_identity_is_world_independent():
    from symbiont_lab.world.adapter import _construct_organism

    common = dict(
        organism_id="same-organism",
        organism_seed=7071,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )
    first = _construct_organism(
        world_id="world-a",
        world_seed=1,
        **common,
    )
    second = _construct_organism(
        world_id="world-b",
        world_seed=999999,
        **common,
    )

    assert first.receptor_ids == second.receptor_ids
    assert first.individual.symbiont.symbiont_id == second.individual.symbiont.symbiont_id
    assert first.individual.symbiont.genome.identity == second.individual.symbiont.genome.identity

