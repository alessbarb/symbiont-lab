from __future__ import annotations

import pytest

from symbiont.core.body_schema import BODY_SCHEMA_VERSION, BodySchemaEngine
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


def test_fresh_body_schema_is_explicitly_undeveloped():
    schema = BodySchemaEngine()

    assert schema.state == "undeveloped"
    assert schema.part_count == 0
    assert schema.export(current_tick=0) == {
        "schema_version": BODY_SCHEMA_VERSION,
        "state": "undeveloped",
        "parts": [],
        "dependencies": [],
        "global_state": {},
    }


def test_established_self_model_evidence_creates_one_opaque_sensory_part():
    schema = BodySchemaEngine()
    schema.observe_self_model({"compute.logical_cpu": _evidence()}, tick=12)

    payload = schema.export(current_tick=12)

    assert payload["state"] == "partial"
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


def test_same_sense_keeps_stable_body_part_identity_and_updates_state():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence(health_class=9)}, tick=5)
    first = schema.export(current_tick=5)["parts"][0]

    schema.observe_self_model({"signal.a": _evidence(health_class=14)}, tick=9)
    second = schema.export(current_tick=9)["parts"][0]

    assert second["part_id"] == first["part_id"]
    assert second["health_class"] == 14


def test_body_schema_does_not_need_topology_or_manifest_truth():
    schema = BodySchemaEngine()
    schema.observe_self_model({"opaque.sense": _evidence()}, tick=1)
    payload = schema.export(current_tick=1)

    serialized = repr(payload)
    assert "node_id" not in serialized
    assert "topology" not in serialized
    assert "provider" not in serialized
    assert "manifest" not in serialized


def test_old_part_ages_to_dormant_without_new_evidence():
    schema = BodySchemaEngine()
    schema.observe_self_model({"signal.a": _evidence()}, tick=0)

    payload = schema.export(current_tick=500)

    assert payload["parts"][0]["recency_class"] == RecencyClass.DORMANT.value


def test_repeated_exported_self_model_entry_does_not_rejuvenate_stale_evidence():
    schema = BodySchemaEngine()
    stale = _evidence(recency_class=RecencyClass.LONG_IDLE.value)

    schema.observe_self_model({"signal.a": stale}, tick=200)
    first = schema.export(current_tick=200)["parts"][0]
    schema.observe_self_model({"signal.a": stale}, tick=201)
    second = schema.export(current_tick=201)["parts"][0]

    assert first["recency_class"] == RecencyClass.LONG_IDLE.value
    assert second["recency_class"] == RecencyClass.LONG_IDLE.value


def test_global_state_is_derived_only_from_part_health_and_confidence():
    schema = BodySchemaEngine()
    schema.observe_self_model(
        {
            "signal.a": _evidence(health_class=10, confidence_class=6),
            "signal.b": _evidence(health_class=14, confidence_class=12),
        },
        tick=2,
    )

    payload = schema.export(current_tick=2)

    assert payload["global_state"] == {"self_model_confidence_class": 9, "integrity_class": 12}


def test_checkpoint_round_trip_preserves_learned_parts_without_raw_sense_ids():
    schema = BodySchemaEngine()
    schema.observe_self_model({"sensitive-capability-name": _evidence()}, tick=100)
    checkpoint = schema.export(current_tick=100)

    restored = BodySchemaEngine.restore(checkpoint, current_tick=100)
    restored_payload = restored.export(current_tick=100)

    assert restored_payload == checkpoint
    assert "sensitive-capability-name" not in repr(restored_payload)


def test_restore_rejects_developed_state_before_that_contract_exists():
    with pytest.raises(ValueError, match="state"):
        BodySchemaEngine.restore(
            {
                "schema_version": BODY_SCHEMA_VERSION,
                "state": "developed",
                "parts": [],
                "dependencies": [],
                "global_state": {},
            },
            current_tick=0,
        )


def test_restore_rejects_dependencies_in_sensory_pr4():
    with pytest.raises(ValueError, match="dependencies"):
        BodySchemaEngine.restore(
            {
                "schema_version": BODY_SCHEMA_VERSION,
                "state": "undeveloped",
                "parts": [],
                "dependencies": [{"source_id": "a", "target_id": "b"}],
                "global_state": {},
            },
            current_tick=0,
        )


def test_evidence_validation_rejects_out_of_range_classes():
    schema = BodySchemaEngine()
    with pytest.raises(ValueError, match="health_class"):
        schema.observe_self_model({"signal.a": _evidence(health_class=16)}, tick=0)
