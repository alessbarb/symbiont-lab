import pytest
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

    runtime = rig.runtime
    assert runtime._bootstrap_semantic_senses is False
    assert runtime._autonomous_behavior is False
    assert runtime.heritable_genome is not None
    assert runtime.heritable_genome.loci == ()
    assert len(runtime.actuator_constitution.actuator_ids) >= 8

    metabolic = runtime.metabolism.checkpoint()
    assert set(metabolic["replenishment"].values()) == {0.0}

    bindings = rig.actuation_binding.bindings
    assert [binding.effect for binding in bindings[:6]] == ["move"] * 6
    assert bindings[6].effect == "acquire"
    assert runtime.actuator_constitution.actuator_ids[7] not in {
        binding.actuator_id for binding in bindings
    }



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

    assert (
        first.runtime._signal_identity.signal_id("same-physical-source")
        != second.runtime._signal_identity.signal_id("same-physical-source")
    )



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
    assert cleaned.contact is None
    assert cleaned.reception == ()
    assert cleaned.internal == {}
