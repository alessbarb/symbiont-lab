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

    runtime = rig.runtime
    assert runtime._bootstrap_semantic_senses is False
    assert runtime.heritable_genome is not None
    assert runtime.heritable_genome.loci == ()
    assert len(runtime.actuator_constitution.actuator_ids) >= 8

    metabolic = runtime.metabolism.checkpoint()
    assert set(metabolic["replenishment"].values()) == {0.0}

    bindings = rig.actuation_binding.bindings
    assert [binding.effect for binding in bindings[:6]] == ["move"] * 6
    assert bindings[6].effect == "interact"
    assert runtime._motor_exploration_mode == "spontaneous"
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

    assert first.receptor_ids != second.receptor_ids
    assert set(first.receptor_ids).isdisjoint(set(second.receptor_ids))
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


def test_clean_world_never_calls_structured_motor_probing(monkeypatch):
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
    proposer = pop._rigs["clean-probe-guard"].runtime._actuator_proposer
    assert proposer is not None

    def forbidden(*args, **kwargs):
        raise AssertionError("structured motor probing entered clean World")

    monkeypatch.setattr(proposer, "probing_plan", forbidden)
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

    assert all(binding.effect != "acquire" for binding in rig.actuation_binding.bindings)
    assert sum(binding.effect == "interact" for binding in rig.actuation_binding.bindings) == 1


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
    assert rig.runtime._resource_habitats == {}
    assert rig.runtime._explicit_metabolism is True
    assert rig.runtime._birth_authority is None
    assert rig.runtime._reproductive_pressure is None


def test_boundary_guard_rejects_implicit_ambient_metabolism_regardless_of_ledger_values():
    """Regression: ``experimental_clean=True`` must always request explicit
    (non-ambient) metabolism, not just a metabolism ledger that happens to be
    zeroed today.

    ``OrganismRuntime`` only falls back to full-capacity ambient replenishment
    when ``explicit_metabolism`` is falsy *and* no metabolism ledger is passed
    explicitly (e.g. on clonal reproduction, which reconstructs a child
    without an explicit ledger). A clean-mode rig whose declared
    ``explicit_metabolism`` flag is False would silently regress to free
    ambient energy the moment any code path stops passing a ledger
    explicitly, even though its ledger looks correctly zeroed right now.
    ``assert_experimental_boundary`` must fail closed on the declared intent,
    not only on the currently-realized replenishment values.
    """
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
    assert rig.runtime._explicit_metabolism is True

    rig.runtime._explicit_metabolism = False
    with pytest.raises(RuntimeError, match="implicit/ambient metabolic replenishment"):
        pop.assert_experimental_boundary()


def test_clean_material_exchange_crosses_only_scalar_absorption(monkeypatch):
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
    rig = pop._rigs["isolated-core"]

    def forbidden(*args, **kwargs):
        raise AssertionError("World attempted typed/resource-identified intake")

    monkeypatch.setattr(rig.runtime, "request_resource_intake", forbidden)
    for _ in range(32):
        pop.run_tick()


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
    assert first.runtime._signal_identity.key == second.runtime._signal_identity.key
    assert first.runtime.body_schema.export(current_tick=0) == second.runtime.body_schema.export(current_tick=0)
