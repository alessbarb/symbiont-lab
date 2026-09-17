from symbiont_lab.integration import IntegratedHabitatConfig, IntegratedHabitatRuntime
from symbiont_lab.studies.integrated_habitat_runtime import run_integrated_habitat_smoke


def test_integrated_habitat_exercises_population_and_existing_channels():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        max_population=4, resource_budget=16.0, trigger_lifecycle_probe=True,
    ))
    history = habitat.run(5)
    assert any(item.births for item in history)
    assert any(item.deaths for item in history)
    assert habitat.authority.lineage_records
    assert habitat.telemetry.events
    assert all(runtime.social_habitat is habitat.social_habitat for runtime in habitat.population.values())


def test_newborn_has_fresh_acquired_state_and_inherited_genome_only():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        max_population=4, resource_budget=16.0, trigger_lifecycle_probe=True,
    ))
    habitat.run(2)
    child_id = next(identifier for identifier in habitat.population if identifier.endswith("-000000"))
    child = habitat.population[child_id]
    assert child.experience_ledger.records == ()
    assert child.social_evidence_ledger.claims == ()
    assert child.sequence_grounding_ledger.exposures == ()
    assert child.genome is not None


def test_integrated_checkpoint_restores_population_identity_and_bounded_history():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        max_population=4, resource_budget=16.0, trigger_lifecycle_probe=True,
    ))
    habitat.run(5)
    restored = IntegratedHabitatRuntime.from_checkpoint(habitat.checkpoint())
    assert tuple(sorted(restored.population)) == tuple(sorted(habitat.population))
    assert restored.dead.keys() == habitat.dead.keys()
    assert restored.tick_count == habitat.tick_count
    assert len(restored.history) <= 256
    assert len(restored.telemetry.events) <= habitat.config.telemetry_max_events


def test_integrated_habitat_rejects_unbounded_configuration():
    try:
        IntegratedHabitatConfig(max_population=33)
    except ValueError:
        pass
    else:
        raise AssertionError("population ceiling must be enforced")


def test_integrated_smoke_replays_and_is_observer_equivalent():
    results = run_integrated_habitat_smoke(seeds=(101, 127, 149), ticks=8)
    assert all(item.checkpoint_round_trip for item in results)
    assert all(item.replay_equal for item in results)
    assert all(item.observer_equivalent for item in results)
    assert all(item.finite_state and item.bounded for item in results)


def test_integrated_history_is_bounded():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        initial_population=1, max_population=1, max_ticks=300,
    ))
    habitat.run(300)
    assert len(habitat.history) <= 256


def test_sequence_transport_capacity_is_bounded_per_tick_for_long_runs():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        initial_population=2, max_population=2, max_ticks=300, channel_max_deliveries=1,
    ))
    habitat.run(300)
    assert habitat.tick_count == 300
    assert habitat.sequence_channel.deliveries <= 1
    assert len(habitat.telemetry.events) <= habitat.config.telemetry_max_events


def test_integrated_habitat_handles_population_extinction_without_crash():
    habitat = IntegratedHabitatRuntime(IntegratedHabitatConfig(
        initial_population=1, max_population=1, resource_budget=1.0,
        trigger_lifecycle_probe=True,
    ))
    history = habitat.run(10)
    assert habitat.population == {}
    assert habitat.dead
    assert any(item.deaths for item in history)
