from __future__ import annotations

import json

import pytest

from symbiont.host.readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)
from symbiont.sensory import SensorySystem, TransductionKind


def reading(
    source: str, value: float, *, quality: ReadingQuality = ReadingQuality.NOMINAL
) -> SensorReading:
    return SensorReading(
        capability_id=source,
        source="test-provider",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=1,
        quality=quality,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_identity_sensor_preserves_legacy_percept_while_owning_sensor_identity() -> None:
    system = SensorySystem()
    percepts = system.transduce(
        [reading("source.a", 0.42)],
        percept_names={"source.a": "sense_opaque"},
        tick=1,
    )

    assert len(percepts) == 1
    percept = percepts[0]
    assert percept.name == "sense_opaque"
    assert percept.value == pytest.approx(0.42)
    assert percept.sensor_id is not None
    assert percept.sensor_id.startswith("sensor.identity.")
    assert percept.modality_id == "modality.identity"
    assert system.sensors[0].source_ids == ("source.a",)


def test_one_source_can_produce_two_distinct_percept_streams() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.opaque"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(
        identity.sensor_id,
        modality_id="modality.alpha",
        transduction=TransductionKind.DIFFERENCE,
        tick=2,
    )

    first = system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.opaque"},
        tick=2,
    )
    second = system.transduce(
        [reading("source.a", 1.75)],
        percept_names={"source.a": "signal.opaque"},
        tick=3,
    )

    first_by_name = {item.name: item for item in first}
    second_by_name = {item.name: item for item in second}
    assert set(second_by_name) == {identity.sensor_id, child.sensor_id}
    assert first_by_name[child.sensor_id].value == pytest.approx(0.0)
    assert second_by_name[identity.sensor_id].value == pytest.approx(1.75)
    assert second_by_name[child.sensor_id].value != second_by_name[identity.sensor_id].value


def test_modalities_are_structurally_non_equivalent() -> None:
    system = SensorySystem()
    by_id = {item.modality_id: item for item in system.modalities}

    assert (
        by_id["modality.alpha"].allowed_transductions
        != by_id["modality.beta"].allowed_transductions
    )
    assert by_id["modality.alpha"].temporal_capacity != by_id["modality.beta"].temporal_capacity
    assert by_id["modality.gamma"].max_inputs > by_id["modality.alpha"].max_inputs


def test_multisource_sensor_combines_sources_without_creating_external_signal() -> None:
    system = SensorySystem(plasticity_enabled=True)
    sensor = system.create_multisource_sensor(("source.a", "source.b"), tick=1)

    percepts = system.transduce(
        [reading("source.a", 0.2), reading("source.b", 0.8)],
        percept_names={"source.a": "signal.a", "source.b": "signal.b"},
        tick=1,
    )
    by_name = {item.name: item for item in percepts}

    assert sensor.sensor_id in by_name
    assert by_name[sensor.sensor_id].value == pytest.approx(0.5)
    assert sensor.source_ids == ("source.a", "source.b")


def test_checkpoint_persists_phenotype_but_not_raw_transient_values() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(identity.sensor_id, modality_id="modality.beta", tick=2)
    system.transduce(
        [reading("source.a", 2.0)],
        percept_names={"source.a": "signal.a"},
        tick=2,
    )

    payload = system.checkpoint()
    encoded = json.dumps(payload)
    assert "previous_input" not in encoded
    assert "last_output" not in encoded
    assert "integrator" not in encoded

    restored = SensorySystem.restore(payload)
    restored_child = next(item for item in restored.sensors if item.sensor_id == child.sensor_id)
    assert restored_child.parent_sensor_ids == (identity.sensor_id,)
    assert restored_child.previous_input is None
    assert restored_child.last_output is None


def test_plastic_step_can_develop_non_identity_receptor_without_target_label() -> None:
    system = SensorySystem(plasticity_enabled=True)
    for tick in range(1, 17):
        system.transduce(
            [reading("source.a", float(tick))],
            percept_names={"source.a": "signal.a"},
            tick=tick,
        )

    mutations = system.plastic_step(tick=16)

    assert any(item.kind.value == "duplicate" for item in mutations)
    variants = [
        sensor for sensor in system.sensors if not sensor.sensor_id.startswith("sensor.identity.")
    ]
    assert len(variants) == 1
    assert variants[0].source_ids == ("source.a",)
    assert variants[0].modality_id == "modality.alpha"


def test_parameter_adaptation_uses_local_response_dynamics_only() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(
        identity.sensor_id,
        modality_id="modality.alpha",
        transduction=TransductionKind.DIFFERENCE,
        tick=2,
    )
    for tick in range(2, 18):
        system.transduce(
            [reading("source.a", 1.0)],
            percept_names={"source.a": "signal.a"},
            tick=tick,
        )

    old_gain = child.gain
    mutations = system.plastic_step(tick=32)

    assert child.gain >= old_gain
    assert any(item.kind.value == "parameter_adjust" for item in mutations)


def test_plastic_step_never_exceeds_mutation_window_budget() -> None:
    system = SensorySystem(plasticity_enabled=True)
    for tick in range(1, 65):
        system.transduce(
            [reading("source.a", 1.0), reading("source.b", 2.0)],
            percept_names={"source.a": "signal.a", "source.b": "signal.b"},
            tick=tick,
        )
        if tick % system.limits.mutation_window_ticks == 0:
            mutations = system.plastic_step(tick=tick)
            assert len(mutations) <= system.limits.max_sensor_mutations_per_window


def test_plastic_step_can_create_multisource_receptor_without_evaluator_pair() -> None:
    system = SensorySystem(plasticity_enabled=True)
    for tick in range(1, 49):
        system.transduce(
            [reading("source.a", float(tick)), reading("source.b", float(tick) * 2.0)],
            percept_names={"source.a": "signal.a", "source.b": "signal.b"},
            tick=tick,
        )
        if tick % system.limits.mutation_window_ticks == 0:
            system.plastic_step(tick=tick)

    multisource = [
        sensor
        for sensor in system.sensors
        if sensor.modality_id == "modality.gamma" and len(sensor.source_ids) == 2
    ]
    assert multisource
    assert multisource[0].source_ids == ("source.a", "source.b")
    assert len(multisource[0].parent_sensor_ids) == 2


def test_adaptive_identity_sensor_keeps_stable_organism_owned_name_when_source_alias_changes() -> (
    None
):
    system = SensorySystem(plasticity_enabled=True)
    first = system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.first"},
        tick=1,
    )[0]
    second = system.transduce(
        [reading("source.a", 2.0)],
        percept_names={"source.a": "sense_later"},
        tick=2,
    )[0]
    assert first.sensor_id == second.sensor_id
    assert first.name == first.sensor_id
    assert second.name == first.sensor_id


def test_restore_accepts_history_for_sensor_that_was_later_pruned() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    first = system.duplicate(identity.sensor_id, modality_id="modality.alpha", tick=2)
    second = system.duplicate(identity.sensor_id, modality_id="modality.alpha", tick=3)
    second.gain = first.gain
    second.decay = first.decay
    first.age_ticks = 40
    second.age_ticks = 40
    first.utility = second.utility = 0.0
    first.utility_observations = second.utility_observations = 8
    system.plastic_step(tick=16)
    payload = system.checkpoint()
    restored = SensorySystem.restore(payload)
    assert restored.mutations == system.mutations


def test_restore_rejects_boolean_numeric_checkpoint_fields() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    payload = system.checkpoint()
    payload["next_sensor_id"] = True
    with pytest.raises(ValueError):
        SensorySystem.restore(payload)


def test_restore_preserves_exact_modality_constitution() -> None:
    system = SensorySystem(plasticity_enabled=True)
    payload = system.checkpoint()
    restored = SensorySystem.restore(payload)
    assert restored.constitution() == system.constitution()


def test_downstream_utility_rewards_only_the_sensor_named_as_predictive_source() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0), reading("source.b", 2.0)],
        percept_names={"source.a": "signal.a", "source.b": "signal.b"},
        tick=1,
    )
    identities = {
        sensor.source_ids[0]: sensor
        for sensor in system.sensors
        if sensor.sensor_id.startswith("sensor.identity.")
    }
    system.update_downstream_utility({identities["source.a"].cognitive_name: 0.8})
    assert identities["source.a"].utility > 0.0
    assert identities["source.b"].utility == 0.0


def test_temporal_sensor_marks_exactly_first_post_restore_output_as_cold_start() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(
        identity.sensor_id,
        modality_id="modality.alpha",
        transduction=TransductionKind.DIFFERENCE,
        tick=2,
    )
    system.transduce(
        [reading("source.a", 1.5)],
        percept_names={"source.a": "signal.a"},
        tick=2,
    )
    payload = system.checkpoint()
    assert "cold_start" not in json.dumps(payload)

    restored = SensorySystem.restore(payload)
    restored_child = next(
        sensor for sensor in restored.sensors if sensor.sensor_id == child.sensor_id
    )
    assert restored_child.cold_start_pending is True

    restored.transduce(
        [reading("source.a", 2.0)],
        percept_names={"source.a": "signal.a"},
        tick=3,
    )
    first_view = next(
        item
        for item in restored.phenotype_view()["sensors"]
        if item["sensor_id"] == child.sensor_id
    )
    assert first_view["cold_start"] is True

    restored.transduce(
        [reading("source.a", 2.5)],
        percept_names={"source.a": "signal.a"},
        tick=4,
    )
    second_view = next(
        item
        for item in restored.phenotype_view()["sensors"]
        if item["sensor_id"] == child.sensor_id
    )
    assert second_view["cold_start"] is False


def test_germinal_copy_inherits_exact_capacity_without_acquired_phenotype() -> None:
    parent = SensorySystem(plasticity_enabled=True)
    parent.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = parent.sensors[0]
    parent.duplicate(identity.sensor_id, modality_id="modality.alpha", tick=2)
    child = parent.germinal_copy()

    assert child.constitution() == parent.constitution()
    assert child.sensors == ()
    assert child.mutations == ()


def test_phenotype_projects_opaque_signal_lineage_for_multisource_sensor() -> None:
    system = SensorySystem(plasticity_enabled=True)
    sensor = system.create_multisource_sensor(("source.a", "source.b"), tick=1)
    view = system.phenotype_view(
        signal_ids_by_source={
            "source.a": "signal.aaaaaaaa",
            "source.b": "signal.bbbbbbbb",
        }
    )
    projected = next(item for item in view["sensors"] if item["sensor_id"] == sensor.sensor_id)
    assert projected["signal_ids"] == ["signal.aaaaaaaa", "signal.bbbbbbbb"]
    assert "source.a" not in repr(view)
    assert "source.b" not in repr(view)


def test_unique_unproductive_sensor_is_pruned_only_after_evaluation_grace() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(identity.sensor_id, modality_id="modality.alpha", tick=2)
    child.age_ticks = 80
    child.utility = 0.0
    child.utility_observations = 0
    system.plastic_step(tick=16)
    assert any(sensor.sensor_id == child.sensor_id for sensor in system.sensors)

    child.utility_observations = 16
    system.plastic_step(tick=32)
    assert all(sensor.sensor_id != child.sensor_id for sensor in system.sensors)


def test_modality_cannot_exceed_sensory_constitution_bounds() -> None:
    from symbiont.sensory.limits import SensoryLimits
    from symbiont.sensory.modalities import SensoryModality

    too_deep = SensoryModality(
        "modality.too-deep",
        (TransductionKind.IDENTITY,),
        max_inputs=1,
        temporal_capacity=65,
        base_cost=0.001,
    )
    identity = next(
        item for item in SensorySystem().modalities if item.modality_id == "modality.identity"
    )
    with pytest.raises(ValueError, match="temporal_capacity"):
        SensorySystem(
            limits=SensoryLimits(max_temporal_depth=64),
            modalities=(identity, too_deep),
        )


def test_acquisition_cost_is_shared_across_receptors_using_same_source() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(identity.sensor_id, modality_id="modality.alpha", tick=2)
    system.update_acquisition_costs({"source.a": 0.02})

    assert identity.acquisition_cost == pytest.approx(0.01)
    assert child.acquisition_cost == pytest.approx(0.01)


def test_multisource_acquisition_cost_sums_allocated_source_shares() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0), reading("source.b", 2.0)],
        percept_names={"source.a": "signal.a", "source.b": "signal.b"},
        tick=1,
    )
    gamma = system.create_multisource_sensor(("source.a", "source.b"), tick=2)
    system.update_acquisition_costs({"source.a": 0.02, "source.b": 0.04})
    # Each source has two consumers: its identity receptor and gamma.
    assert gamma.acquisition_cost == pytest.approx(0.03)


def test_known_source_without_raw_sample_does_not_fabricate_sensor() -> None:
    system = SensorySystem(plasticity_enabled=True)
    percepts = system.transduce(
        [],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    assert percepts == ()
    assert system.sensors == ()


def test_v1_sensory_checkpoint_migrates_to_v2_with_empty_selection_state() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    payload = system.checkpoint()
    payload["schema_version"] = 1
    payload.pop("selection", None)
    payload["constitution"] = dict(payload["constitution"])
    payload["constitution"]["schema_version"] = 1
    payload["constitution"].pop("selection_schema_version", None)

    restored = SensorySystem.restore(payload)

    assert restored.selection_credits == {}
    assert [sensor.checkpoint() for sensor in restored.sensors] == [
        sensor.checkpoint() for sensor in system.sensors
    ]


def test_sensory_selection_checkpoint_contains_no_raw_previous_percept_value() -> None:
    system = SensorySystem(plasticity_enabled=True)
    for tick in range(1, 40):
        system.transduce(
            [reading("source.a", float(tick)), reading("source.b", float(tick - 1))],
            percept_names={"source.a": "signal.a", "source.b": "signal.b"},
            tick=tick,
        )
    encoded = json.dumps(system.checkpoint(), sort_keys=True)
    assert "last_target" not in encoded
    assert '"previous"' not in encoded


def test_phenotype_view_exposes_current_substrate_without_source_semantics() -> None:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [reading("source.a", 1.0)],
        percept_names={"source.a": "signal.a"},
        tick=1,
    )
    identity = system.sensors[0]
    child = system.duplicate(
        identity.sensor_id,
        modality_id="modality.alpha",
        transduction=TransductionKind.DIFFERENCE,
        tick=2,
    )

    payload = system.phenotype_view(signal_ids_by_source={"source.a": "signal." + "a" * 64})
    sensor = next(item for item in payload["sensors"] if item["sensor_id"] == child.sensor_id)
    modality = next(
        item for item in payload["modalities"] if item["modality_id"] == "modality.alpha"
    )

    assert sensor["sample_geometry"] == "scalar"
    assert sensor["transduction"] == "difference"
    assert sensor["signal_ids"] == ["signal." + "a" * 64]
    assert "difference" in modality["allowed_transductions"]
    assert "source.a" not in json.dumps(payload)


def test_capacity_pressure_skips_new_identity_source_without_terminating() -> None:
    from symbiont.sensory.limits import SensoryLimits

    system = SensorySystem(
        plasticity_enabled=True,
        limits=SensoryLimits(max_active_sensors=2),
    )
    first = system.transduce(
        [reading("source.a", 1.0), reading("source.b", 2.0)],
        percept_names={"source.a": "signal.a", "source.b": "signal.b"},
        tick=1,
    )
    assert len(first) == 2

    second = system.transduce(
        [reading("source.a", 3.0), reading("source.b", 4.0), reading("source.c", 5.0)],
        percept_names={
            "source.a": "signal.a",
            "source.b": "signal.b",
            "source.c": "signal.c",
        },
        tick=2,
    )

    assert len(second) == 2
    assert len(system.sensors) == 2
    phenotype = system.phenotype_view()
    assert phenotype["summary"]["capacity_saturated"] is True
    assert phenotype["summary"]["capacity_rejections"] == 1


def test_plastic_step_does_not_overflow_full_sensor_capacity() -> None:
    from symbiont.sensory.limits import SensoryLimits

    system = SensorySystem(
        plasticity_enabled=True,
        limits=SensoryLimits(max_active_sensors=1),
    )
    for tick in range(1, 17):
        system.transduce(
            [reading("source.a", float(tick))],
            percept_names={"source.a": "signal.a"},
            tick=tick,
        )

    assert system.plastic_step(tick=16) == ()
    assert len(system.sensors) == 1


def test_capacity_rejections_are_checkpointed_as_bounded_aggregate() -> None:
    from symbiont.sensory.limits import SensoryLimits

    system = SensorySystem(
        plasticity_enabled=True,
        limits=SensoryLimits(max_active_sensors=1),
    )
    system.transduce(
        [reading("source.a", 1.0), reading("source.b", 2.0)],
        percept_names={"source.a": "signal.a", "source.b": "signal.b"},
        tick=1,
    )
    restored = SensorySystem.restore(system.checkpoint())
    assert restored.phenotype_view()["summary"]["capacity_rejections"] == 1
