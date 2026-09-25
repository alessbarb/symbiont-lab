from __future__ import annotations

import pytest
from symbiont.core.body_schema import (
    BODY_SCHEMA_VERSION,
    LEGACY_BODY_SCHEMA_VERSION,
    MAX_SENSORY_PARTS,
    BodySchemaEngine,
)
from symbiont.core.selfmodel import RecencyClass


def _evidence(**overrides):
    entry = {
        "cost_class": 3,
        "health_class": 12,
        "confidence_class": 10,
        "maturity_class": 6,
        "recency_class": RecencyClass.CURRENT.value,
    }
    entry.update(overrides)
    return entry


def _empty_checkpoint(**overrides):
    payload = {
        "schema_version": BODY_SCHEMA_VERSION,
        "state": "undeveloped",
        "parts": [],
        "dependencies": [],
        "global_state": {},
        "id_salt": "0" * 32,
        "cognitive_learning": {
            "channel_support": [],
            "coactivity_support": [],
            "regions": [],
            "dependency_evidence": [],
        },
    }
    payload.update(overrides)
    return payload


def test_fresh_body_schema_is_explicitly_undeveloped():
    schema = BodySchemaEngine()

    assert schema.state == "undeveloped"
    assert schema.part_count == 0
    assert schema.export_representation(current_tick=0) == {
        "schema_version": BODY_SCHEMA_VERSION,
        "state": "undeveloped",
        "parts": [],
        "dependencies": [],
        "global_state": {},
    }


def test_established_self_model_evidence_creates_one_opaque_sensory_part():
    schema = BodySchemaEngine()
    schema.observe_self_model({"compute.logical_cpu": _evidence()}, tick=12)

    payload = schema.export_representation(current_tick=12)

    assert payload["state"] == "developing"
    assert len(payload["parts"]) == 1
    part = payload["parts"][0]
    assert part["kind"] == "sense"
    assert part["part_id"].startswith("part.sense.")
    assert len(part["part_id"].removeprefix("part.sense.")) == 32
    assert "compute" not in part["part_id"]
    assert "cpu" not in part["part_id"]
    assert part["health_class"] == 12
    assert part["confidence_class"] == 10
    assert part["cost_class"] == 3
    assert part["maturity_class"] == 6
    assert part["existence_confidence_class"] == 13
    assert payload["dependencies"] == []
    assert payload["global_state"] == {}


def test_same_sense_keeps_stable_body_part_identity_and_updates_state():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence(health_class=9)}, tick=5)
    first = schema.export_representation(current_tick=5)["parts"][0]

    schema.observe_self_model({"signal.a": _evidence(health_class=14)}, tick=9)
    second = schema.export_representation(current_tick=9)["parts"][0]

    assert second["part_id"] == first["part_id"]
    assert second["health_class"] == 14


def test_equal_sense_ids_are_not_linkable_across_fresh_organisms():
    first = BodySchemaEngine()
    second = BodySchemaEngine()
    first.observe_self_model({"signal.same": _evidence()}, tick=1)
    second.observe_self_model({"signal.same": _evidence()}, tick=1)

    first_id = first.export_representation(current_tick=1)["parts"][0]["part_id"]
    second_id = second.export_representation(current_tick=1)["parts"][0]["part_id"]

    assert first_id != second_id


def test_observer_representation_never_exports_private_id_salt():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence()}, tick=1)

    representation = schema.export_representation(current_tick=1)
    checkpoint = schema.export(current_tick=1)

    assert "id_salt" not in representation
    assert "cognitive_learning" not in representation
    assert isinstance(checkpoint["id_salt"], str)
    assert len(checkpoint["id_salt"]) == 32


def test_body_schema_does_not_need_topology_or_manifest_truth():
    schema = BodySchemaEngine()
    schema.observe_self_model({"opaque.sense": _evidence()}, tick=1)
    payload = schema.export_representation(current_tick=1)

    serialized = repr(payload)
    assert "node_id" not in serialized
    assert "topology" not in serialized
    assert "provider" not in serialized
    assert "manifest" not in serialized


def test_old_part_ages_to_dormant_without_new_evidence():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence()}, tick=0)

    payload = schema.export_representation(current_tick=500)

    assert payload["parts"][0]["recency_class"] == RecencyClass.DORMANT.value


def test_repeated_exported_self_model_entry_does_not_rejuvenate_stale_evidence():
    schema = BodySchemaEngine()
    stale = _evidence(recency_class=RecencyClass.LONG_IDLE.value)

    schema.observe_self_model({"signal.a": stale}, tick=200)
    first = schema.export_representation(current_tick=200)["parts"][0]
    schema.observe_self_model({"signal.a": stale}, tick=201)
    second = schema.export_representation(current_tick=201)["parts"][0]

    assert first["recency_class"] == RecencyClass.LONG_IDLE.value
    assert second["recency_class"] == RecencyClass.LONG_IDLE.value


def test_longitudinal_sense_churn_never_exceeds_sensory_part_bound():
    schema = BodySchemaEngine()
    initial = {
        f"signal.{index}": _evidence(recency_class=RecencyClass.DORMANT.value)
        for index in range(MAX_SENSORY_PARTS)
    }
    schema.observe_self_model(initial, tick=500)
    before_ids = {
        part["part_id"]
        for part in schema.export_representation(current_tick=500)["parts"]
        if part["kind"] == "sense"
    }
    assert schema.sensory_part_count == MAX_SENSORY_PARTS

    schema.observe_self_model({"signal.new": _evidence()}, tick=900)
    payload = schema.export_representation(current_tick=900)
    after_ids = {part["part_id"] for part in payload["parts"] if part["kind"] == "sense"}

    assert schema.sensory_part_count == MAX_SENSORY_PARTS
    assert len(after_ids) == MAX_SENSORY_PARTS
    assert len(after_ids - before_ids) == 1
    assert len(before_ids - after_ids) == 1


def test_global_state_remains_empty_until_global_integrity_learning_phase():
    schema = BodySchemaEngine()
    schema.observe_self_model(
        {
            "signal.a": _evidence(health_class=10, confidence_class=6),
            "signal.b": _evidence(health_class=14, confidence_class=12),
        },
        tick=2,
    )

    payload = schema.export_representation(current_tick=2)

    assert payload["global_state"] == {}


def test_checkpoint_round_trip_preserves_identity_and_learned_parts_without_raw_sense_ids():
    schema = BodySchemaEngine()
    schema.observe_self_model({"sensitive-capability-name": _evidence()}, tick=100)
    checkpoint = schema.export(current_tick=100)
    representation = schema.export_representation(current_tick=100)

    restored = BodySchemaEngine.restore(checkpoint, current_tick=100)

    assert restored.export(current_tick=100) == checkpoint
    assert restored.export_representation(current_tick=100) == representation
    assert "sensitive-capability-name" not in repr(checkpoint)


def test_restored_private_salt_keeps_identity_stable_for_future_observations():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence()}, tick=10)
    original_id = schema.export_representation(current_tick=10)["parts"][0]["part_id"]
    checkpoint = schema.export(current_tick=10)

    restored = BodySchemaEngine.restore(checkpoint, current_tick=10)
    restored.observe_self_model({"signal.a": _evidence(health_class=14)}, tick=11)
    parts = restored.export_representation(current_tick=11)["parts"]

    assert len(parts) == 1
    assert parts[0]["part_id"] == original_id
    assert parts[0]["health_class"] == 14


def test_restore_rejects_developed_state_before_that_contract_exists():
    with pytest.raises(ValueError, match="state"):
        BodySchemaEngine.restore(_empty_checkpoint(state="developed"), current_tick=0)


def test_legacy_restore_rejects_dependencies():
    payload = _empty_checkpoint(
        schema_version=LEGACY_BODY_SCHEMA_VERSION,
        dependencies=[{"source_id": "a", "target_id": "b"}],
    )
    payload.pop("cognitive_learning")
    with pytest.raises(ValueError, match="legacy.*dependencies"):
        BodySchemaEngine.restore(payload, current_tick=0)


def test_restore_rejects_nonempty_global_state():
    with pytest.raises(ValueError, match="global_state"):
        BodySchemaEngine.restore(
            _empty_checkpoint(global_state={"integrity_class": 15}), current_tick=0
        )


def test_restore_rejects_missing_private_id_salt():
    payload = _empty_checkpoint()
    payload.pop("id_salt")
    with pytest.raises(ValueError, match="id_salt"):
        BodySchemaEngine.restore(payload, current_tick=0)


def test_restore_rejects_contradictory_derived_existence_confidence():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence(maturity_class=6)}, tick=1)
    payload = schema.export(current_tick=1)
    payload["parts"][0]["existence_confidence_class"] = 0

    with pytest.raises(ValueError, match="contradicts"):
        BodySchemaEngine.restore(payload, current_tick=1)


def test_evidence_validation_rejects_out_of_range_classes():
    schema = BodySchemaEngine()
    with pytest.raises(ValueError, match="health_class"):
        schema.observe_self_model({"signal.a": _evidence(health_class=16)}, tick=0)
