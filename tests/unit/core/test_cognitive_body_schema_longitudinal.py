from copy import deepcopy

from symbiont.core.body_schema import MAX_COGNITIVE_REGION_MEMBERS, BodySchemaEngine


def _channel(index):
    return f"channel.cognition.{index:032x}"


def _observation(*entries):
    return {"schema_version": 1, "channels": [
        {"channel_id": _channel(index), "activity_class": activity}
        for index, activity in entries
    ]}


def _learn_singleton(schema, index, tick):
    for _ in range(4):
        schema.observe_cognition(_observation((index, 12)), tick=tick)
        tick += 1
    return tick


def test_saturated_dependency_counters_remain_revisable():
    schema = BodySchemaEngine(id_salt="a" * 32)
    tick = _learn_singleton(schema, 1, 0)
    tick = _learn_singleton(schema, 2, tick)
    for _ in range(300):
        schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
        tick += 1
    assert any(x["relation"] == "co_acts_with" for x in schema.export_representation(current_tick=tick)["dependencies"])

    for _ in range(300):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
    assert not any(x["relation"] == "co_acts_with" for x in schema.export_representation(current_tick=tick)["dependencies"])
    for item in schema.export(current_tick=tick)["cognitive_learning"]["dependency_evidence"]:
        assert 0 <= item["support_count"] <= item["opportunity_count"] <= 255


def test_longitudinal_region_membership_above_tick_budget_round_trips():
    schema = BodySchemaEngine(id_salt="b" * 32)
    tick = _learn_singleton(schema, 0, 0)
    target = min(40, MAX_COGNITIVE_REGION_MEMBERS)
    for index in range(1, target):
        for _ in range(4):
            schema.observe_cognition(_observation((0, 12), (index, 11)), tick=tick)
            tick += 1

    checkpoint = schema.export(current_tick=tick)
    regions = checkpoint["cognitive_learning"]["regions"]
    assert len(regions) == 1
    assert len(regions[0]["members"]) == target > 32
    restored = BodySchemaEngine.restore(deepcopy(checkpoint), current_tick=tick)
    assert restored.export(current_tick=tick) == checkpoint
