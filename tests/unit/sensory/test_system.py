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


def reading(source: str, value: float, *, quality: ReadingQuality = ReadingQuality.NOMINAL) -> SensorReading:
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
    assert percept.source_ids == ("source.a",)


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
    assert set(second_by_name) == {"signal.opaque", child.sensor_id}
    assert first_by_name[child.sensor_id].value == pytest.approx(0.0)
    assert second_by_name["signal.opaque"].value == pytest.approx(1.75)
    assert second_by_name[child.sensor_id].value != second_by_name["signal.opaque"].value


def test_modalities_are_structurally_non_equivalent() -> None:
    system = SensorySystem()
    by_id = {item.modality_id: item for item in system.modalities}

    assert by_id["modality.alpha"].allowed_transductions != by_id["modality.beta"].allowed_transductions
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
    assert by_name[sensor.sensor_id].source_ids == ("source.a", "source.b")


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
    variants = [sensor for sensor in system.sensors if not sensor.sensor_id.startswith("sensor.identity.")]
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
