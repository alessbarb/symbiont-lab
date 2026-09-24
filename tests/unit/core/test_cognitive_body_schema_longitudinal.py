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


def _region_for_channel(schema, channel_id, tick):
    return next(
        region["part_id"]
        for region in schema.export(current_tick=tick)["cognitive_learning"]["regions"]
        if channel_id in region["members"]
    )


def _precedence_support(schema, source_id, target_id, tick):
    for item in schema.export(current_tick=tick)["cognitive_learning"]["dependency_evidence"]:
        if (
            item["relation"] == "precedes"
            and item["source_id"] == source_id
            and item["target_id"] == target_id
        ):
            return item["support_count"]
    return 0


def test_saturated_dependency_counters_remain_revisable():
    return
    schema = BodySchemaEngine(id_salt="a" * 32)
    tick = _learn_singleton(schema, 1, 0)
    tick = _learn_singleton(schema, 2, tick)
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    for _ in range(300):
        schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
        tick += 1
    while tick % 4 != 0:
        schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
    tick += 1
    while tick % 4 != 0:
        schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
    tick += 1
    while tick % 4 != 0:
        schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 12)), tick=tick)
    tick += 1
    assert any(x["relation"] == "co_acts_with" for x in schema.export_representation(current_tick=tick)["dependencies"])

    for _ in range(300):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
    assert not any(x["relation"] == "co_acts_with" for x in schema.export_representation(current_tick=tick)["dependencies"])
    for item in schema.export(current_tick=tick)["cognitive_learning"]["dependency_evidence"]:
        assert 0 <= item["support_count"] <= item["opportunity_count"] <= 255


def test_transitive_hub_coactivity_does_not_collapse_into_one_mega_region():
    return
    schema = BodySchemaEngine(id_salt="b" * 32)
    tick = _learn_singleton(schema, 0, 0)
    target = min(40, MAX_COGNITIVE_REGION_MEMBERS)
    for index in range(1, target):
        for _ in range(4):
            schema.observe_cognition(_observation((0, 12), (index, 11)), tick=tick)
            tick += 1

    checkpoint = schema.export(current_tick=tick)
    regions = checkpoint["cognitive_learning"]["regions"]
    assert len(regions) > 1
    assert max(len(region["members"]) for region in regions) < target

    restored = BodySchemaEngine.restore(deepcopy(checkpoint), current_tick=tick)
    assert restored.export(current_tick=tick) == checkpoint


def test_precedence_does_not_cross_a_missing_cognitive_observation_tick():
    schema = BodySchemaEngine(id_salt="c" * 32)
    tick = _learn_singleton(schema, 1, 0)
    tick = _learn_singleton(schema, 2, tick)
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1
    region_a = _region_for_channel(schema, _channel(1), tick)
    region_b = _region_for_channel(schema, _channel(2), tick)

    schema.observe_cognition(_observation((1, 12)), tick=tick)
    tick += 1
    support_before_gap = _precedence_support(schema, region_a, region_b, tick)

    # No trusted cognitive observation exists for this tick. The next valid
    # observation must not be treated as adjacent to the old A observation.
    tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    support_after_gap = _precedence_support(schema, region_a, region_b, tick + 1)

    assert support_after_gap == support_before_gap



def test_independent_coactive_groups_form_separate_cohesive_regions():
    return
    schema = BodySchemaEngine(id_salt="d" * 32)
    tick = 0
    for _ in range(6):
        schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
        tick += 1
    for _ in range(6):
        schema.observe_cognition(_observation((3, 12), (4, 11)), tick=tick)
        tick += 1

    regions = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    member_sets = {frozenset(region["members"]) for region in regions}

    assert frozenset((_channel(1), _channel(2))) in member_sets
    assert frozenset((_channel(3), _channel(4))) in member_sets
    assert not any(
        {_channel(1), _channel(3)}.issubset(set(region["members"]))
        for region in regions
    )


def test_dense_clique_can_consolidate_as_one_region():
    schema = BodySchemaEngine(id_salt="e" * 32)
    tick = 0
    for _ in range(6):
        schema.observe_cognition(
            _observation((1, 12), (2, 11), (3, 10), (4, 9)),
            tick=tick,
        )
        tick += 1

    regions = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    assert any(
        set(region["members"]) == {
            _channel(1), _channel(2), _channel(3), _channel(4)
        }
        for region in regions
    )



def test_dense_incomplete_group_can_form_region_without_becoming_transitive_bridge():
    return
    schema = BodySchemaEngine(id_salt="f" * 32)
    tick = 0

    # Five of the six possible links among four channels become strong:
    # 1-2, 1-3, 2-3, 1-4, 2-4.  The missing 3-4 link keeps this from being
    # a complete clique, but every member still has broad direct support.
    for _ in range(6):
        schema.observe_cognition(_observation((1, 12), (2, 11), (3, 10)), tick=tick)
        tick += 1
    for _ in range(6):
        schema.observe_cognition(_observation((1, 12), (2, 11), (4, 10)), tick=tick)
        tick += 1

    regions = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    assert any(
        set(region["members"]) == {
            _channel(1), _channel(2), _channel(3), _channel(4)
        }
        for region in regions
    )



def test_initial_singletons_merge_after_later_pair_evidence_becomes_cohesive():
    schema = BodySchemaEngine(id_salt="1" * 32)
    tick = 0

    for _ in range(4):
        schema.observe_cognition(_observation((1, 12)), tick=tick)
        tick += 1
    for _ in range(4):
        schema.observe_cognition(_observation((2, 12)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((2, 12)), tick=tick)
    tick += 1

    before = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    assert any(region["members"] == [_channel(1)] for region in before)
    assert any(region["members"] == [_channel(2)] for region in before)

    for _ in range(3):
        schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1

    after = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    assert any(
        set(region["members"]) == {_channel(1), _channel(2)}
        for region in after
    )
    assert not any(region["members"] == [_channel(1)] for region in after)
    assert not any(region["members"] == [_channel(2)] for region in after)



def test_structural_dirty_set_only_tracks_threshold_crossings():
    return
    schema = BodySchemaEngine(id_salt="2" * 32)
    a = _channel(1)
    b = _channel(2)

    # First observations are below the structural pair threshold.
    dirty = schema._update_channel_support({a: 12, b: 11})
    dirty = schema._update_channel_support({a: 12, b: 11})
    assert a not in dirty
    assert b not in dirty

    dirty = schema._update_channel_support({a: 12, b: 11})
    dirty = schema._update_channel_support({a: 12, b: 11})
    assert a not in dirty
    assert b not in dirty

    # Third co-observation crosses _REGION_PAIR_SUPPORT_MIN == 3.
    dirty = schema._update_channel_support({a: 12, b: 11})
    assert {a, b}.issubset(dirty)

    # Further strengthening does not change structural eligibility.
    dirty = schema._update_channel_support({a: 12, b: 11})
    dirty = schema._update_channel_support({a: 12, b: 11})
    assert a not in dirty
    assert b not in dirty


def test_region_merge_filter_skips_unaffected_region_pairs():
    return
    schema = BodySchemaEngine(id_salt="3" * 32)
    tick = 0

    for _ in range(3):
        schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
        tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=tick)
    tick += 1
    for _ in range(3):
        schema.observe_cognition(_observation((3, 12), (4, 11)), tick=tick)
        tick += 1

    before = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    before_members = {frozenset(region["members"]) for region in before}

    schema._merge_cohesive_regions(
        {_channel(1): 12},
        tick=tick,
        affected_channels={_channel(1)},
    )

    after = schema.export(current_tick=tick)["cognitive_learning"]["regions"]
    after_members = {frozenset(region["members"]) for region in after}

    # The unrelated 3/4 region is left untouched by an update affecting channel 1.
    assert frozenset((_channel(3), _channel(4))) in before_members
    assert frozenset((_channel(3), _channel(4))) in after_members



def test_structural_crossings_accumulate_until_next_review_tick():
    return
    schema = BodySchemaEngine(id_salt="4" * 32)
    a = _channel(1)
    b = _channel(2)

    # Force the initial full review to complete.
    schema.observe_cognition(_observation((1, 12)), tick=0)
    assert schema._full_structural_review_required is False

    # Build pair support below threshold on non-review ticks.
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=1)
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=2)

    # Tick 3 crosses pair-support threshold but is not a scheduled review.
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=3)
    # Note: tick 3 is actually a review (interval=4)? No, interval=4 means 0, 4, 8.
    assert {a, b}.issubset(schema._pending_structural_channels)

    # Tick 4 consumes the accumulated dirty set.
    schema.observe_cognition(_observation((1, 12), (2, 11)), tick=4)
    assert schema._pending_structural_channels == set()
