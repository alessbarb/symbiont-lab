from __future__ import annotations

from copy import deepcopy

from symbiont.core.body_schema import (
    BODY_SCHEMA_VERSION,
    LEGACY_BODY_SCHEMA_VERSION,
    MAX_COGNITIVE_REGIONS,
    BodySchemaEngine,
)


def _channel(index: int) -> str:
    return f"channel.cognition.{index:032x}"


def _observation(*entries: tuple[int, int]):
    return {
        "schema_version": 1,
        "channels": [
            {"channel_id": _channel(index), "activity_class": activity}
            for index, activity in entries
        ],
    }


def _learn_singleton(schema: BodySchemaEngine, index: int, *, start_tick: int) -> int:
    tick = start_tick
    for _ in range(4):
        schema.observe_cognition(_observation((index, 12)), tick=tick)
        tick += 1
    return tick


def _regions(schema: BodySchemaEngine, tick: int):
    return [
        part
        for part in schema.export_representation(current_tick=tick)["parts"]
        if part["kind"] == "cognitive_region"
    ]


def test_transient_internal_activity_does_not_create_region():
    schema = BodySchemaEngine(id_salt="1" * 32)
    for tick in range(3):
        schema.observe_cognition(_observation((1, 12)), tick=tick)

    assert _regions(schema, 3) == []


def test_repeated_internal_activity_consolidates_opaque_region():
    schema = BodySchemaEngine(id_salt="1" * 32)
    end_tick = _learn_singleton(schema, 1, start_tick=0)

    regions = _regions(schema, end_tick)
    assert len(regions) == 1
    region = regions[0]
    assert region["part_id"].startswith("part.region.")
    assert region["kind"] == "cognitive_region"
    assert "channel.cognition" not in repr(schema.export_representation(current_tick=end_tick))
    assert set(region) == {
        "part_id",
        "kind",
        "existence_confidence_class",
        "confidence_class",
        "activity_class",
        "maturity_class",
        "recency_class",
    }


def test_established_regions_do_not_merge_merely_because_they_later_coact():
    schema = BodySchemaEngine(id_salt="2" * 32)
    tick = _learn_singleton(schema, 1, start_tick=0)
    tick = _learn_singleton(schema, 2, start_tick=tick)
    assert len(_regions(schema, tick)) == 2

    for _ in range(10):
        schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
        tick += 1

    assert len(_regions(schema, tick)) == 2
    dependencies = schema.export_representation(current_tick=tick)["dependencies"]
    assert any(item["relation"] == "co_acts_with" for item in dependencies)


def test_alternating_regions_learn_directional_precedence():
    schema = BodySchemaEngine(id_salt="3" * 32)
    tick = _learn_singleton(schema, 1, start_tick=0)
    tick = _learn_singleton(schema, 2, start_tick=tick)
    regions = _regions(schema, tick)
    assert len(regions) == 2

    for _ in range(8):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
        schema.observe_cognition(_observation((2, 12)), tick=tick)
        tick += 1

    dependencies = schema.export_representation(current_tick=tick)["dependencies"]
    precedes = [item for item in dependencies if item["relation"] == "precedes"]
    assert precedes
    assert all(item["source_id"].startswith("part.region.") for item in precedes)
    assert all(item["target_id"].startswith("part.region.") for item in precedes)


def test_dependency_confidence_can_fall_after_unsupported_opportunities():
    schema = BodySchemaEngine(id_salt="4" * 32)
    tick = _learn_singleton(schema, 1, start_tick=0)
    tick = _learn_singleton(schema, 2, start_tick=tick)

    for _ in range(8):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
        schema.observe_cognition(_observation((2, 12)), tick=tick)
        tick += 1
    assert any(item["relation"] == "precedes" for item in schema.export_representation(current_tick=tick)["dependencies"])

    for _ in range(16):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
        schema.observe_cognition(_observation(), tick=tick)
        tick += 1

    dependencies = schema.export_representation(current_tick=tick)["dependencies"]
    assert not any(item["relation"] == "precedes" for item in dependencies)


def test_cognitive_region_count_remains_bounded_under_channel_churn():
    schema = BodySchemaEngine(id_salt="5" * 32)
    tick = 0
    for index in range(MAX_COGNITIVE_REGIONS + 5):
        tick = _learn_singleton(schema, index, start_tick=tick)

    assert schema.cognitive_region_count == MAX_COGNITIVE_REGIONS
    assert len(_regions(schema, tick)) == MAX_COGNITIVE_REGIONS


def test_v2_checkpoint_round_trip_preserves_regions_dependencies_and_hides_channels_from_observer():
    schema = BodySchemaEngine(id_salt="6" * 32)
    tick = _learn_singleton(schema, 1, start_tick=0)
    tick = _learn_singleton(schema, 2, start_tick=tick)
    for _ in range(8):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
        schema.observe_cognition(_observation((2, 12)), tick=tick)
        tick += 1

    checkpoint = schema.export(current_tick=tick)
    representation = schema.export_representation(current_tick=tick)
    restored = BodySchemaEngine.restore(deepcopy(checkpoint), current_tick=tick)

    assert checkpoint["schema_version"] == BODY_SCHEMA_VERSION
    assert "channel.cognition" in repr(checkpoint["cognitive_learning"])
    assert "channel.cognition" not in repr(representation)
    assert restored.export_representation(current_tick=tick) == representation
    assert restored.export(current_tick=tick) == checkpoint


def test_precedence_does_not_bridge_checkpoint_restart_boundary():
    schema = BodySchemaEngine(id_salt="7" * 32)
    tick = _learn_singleton(schema, 1, start_tick=0)
    tick = _learn_singleton(schema, 2, start_tick=tick)
    schema.observe_cognition(_observation((1, 12)), tick=tick)
    tick += 1

    restored = BodySchemaEngine.restore(schema.export(current_tick=tick), current_tick=tick)
    restored.observe_cognition(_observation((2, 12)), tick=tick)

    dependencies = restored.export_representation(current_tick=tick + 1)["dependencies"]
    assert dependencies == []


def test_legacy_v1_sensory_checkpoint_migrates_without_changing_part_identity():
    schema = BodySchemaEngine(id_salt="8" * 32)
    schema.observe_self_model(
        {
            "signal.a": {
                "cost_class": 3,
                "health_class": 12,
                "confidence_class": 10,
                "maturity_class": 6,
                "recency_class": 0,
            }
        },
        tick=10,
    )
    current = schema.export(current_tick=10)
    sense_id = next(part["part_id"] for part in current["parts"] if part["kind"] == "sense")
    legacy = deepcopy(current)
    legacy["schema_version"] = LEGACY_BODY_SCHEMA_VERSION
    legacy["dependencies"] = []
    legacy.pop("cognitive_learning")

    restored = BodySchemaEngine.restore(legacy, current_tick=10)
    migrated = restored.export_representation(current_tick=10)

    assert migrated["schema_version"] == BODY_SCHEMA_VERSION
    assert next(part["part_id"] for part in migrated["parts"] if part["kind"] == "sense") == sense_id
    assert migrated["dependencies"] == []
    assert migrated["global_state"] == {}
