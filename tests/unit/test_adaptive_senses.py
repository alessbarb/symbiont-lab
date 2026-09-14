from symbiont.host.adaptive import AdaptiveSenseModel
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


def reading(capability_id: str, value: float, tick: int) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="fake",
        value=value,
        unit=Unit.COUNT,
        monotonic_timestamp_ns=tick,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_unknown_signal_becomes_opaque_learned_sense() -> None:
    model = AdaptiveSenseModel(min_samples=3, active_limit=2)
    for tick, value in enumerate((10.0, 20.0, 5.0), start=1):
        model.observe((reading("candidate.internal", value, tick),))

    mapping = model.percept_names()
    assert set(mapping) == {"candidate.internal"}
    assert mapping["candidate.internal"].startswith("sense_")
    assert "candidate" not in mapping["candidate.internal"]


def test_constant_signal_loses_to_informative_signal_when_capacity_is_bounded() -> None:
    model = AdaptiveSenseModel(min_samples=3, active_limit=1)
    for tick in range(1, 6):
        model.observe(
            (
                reading("constant", 1.0, tick),
                reading("changing", float(tick * tick), tick),
            )
        )
    assert set(model.percept_names()) == {"changing"}


def test_sensory_development_round_trips_without_raw_history_or_latest_value() -> None:
    model = AdaptiveSenseModel(min_samples=2, active_limit=3)
    model.observe((reading("x", 1.0, 1),))
    model.observe((reading("x", 3.0, 2),))
    payload = model.export()
    assert "last_value" not in payload["states"][0]

    restored = AdaptiveSenseModel.restore(payload)
    assert restored.percept_names() == model.percept_names()
    assert restored.states[0].samples == 2
    assert restored.states[0].last_value is None
    assert not hasattr(restored.states[0], "history")


def test_model_learns_same_tick_and_lagged_relations_without_semantic_labels() -> None:
    model = AdaptiveSenseModel(
        min_samples=2,
        active_limit=3,
        min_relation_samples=3,
        relation_window=3,
    )
    previous_x = 0.0
    for tick in range(1, 10):
        x = float(tick * tick)
        y = x * 3.0 + 7.0
        z = previous_x * 2.0 + 5.0
        model.observe(
            (
                reading("raw-x", x, tick),
                reading("raw-y", y, tick),
                reading("raw-z", z, tick),
            )
        )
        previous_x = x

    relations = model.strongest_relations(limit=8)
    assert relations
    assert all(item.sense_a.startswith("sense_") and item.sense_b.startswith("sense_") for item in relations)
    assert any(item.synchronous is not None and abs(item.synchronous) > 0.99 for item in relations)
    assert any(
        value is not None and abs(value) > 0.99
        for item in relations
        for value in (item.a_to_b, item.b_to_a)
    )


def test_highly_redundant_sense_is_skipped_when_complementary_signal_exists() -> None:
    model = AdaptiveSenseModel(
        min_samples=3,
        active_limit=2,
        min_relation_samples=4,
        redundancy_threshold=0.95,
        relation_window=3,
    )
    for tick in range(1, 12):
        base = float(tick * tick + tick)
        duplicate = base * 4.0 + 1.0
        complementary = float((tick % 3) * 10 + tick * 0.25)
        model.observe(
            (
                reading("base", base, tick),
                reading("duplicate", duplicate, tick),
                reading("complementary", complementary, tick),
            )
        )

    selected = set(model.percept_names())
    assert "complementary" in selected
    assert len(selected.intersection({"base", "duplicate"})) == 1


def test_relations_round_trip_as_aggregate_statistics_only() -> None:
    model = AdaptiveSenseModel(min_samples=2, active_limit=2, min_relation_samples=3)
    for tick in range(1, 7):
        model.observe((reading("a", float(tick), tick), reading("b", float(tick * 2), tick)))

    payload = model.export()
    assert payload["relations"]
    assert "values" not in payload["relations"][0]
    restored = AdaptiveSenseModel.restore(payload)
    assert restored.strongest_relations() == model.strongest_relations()


def test_early_development_samples_only_a_bounded_rotating_slice() -> None:
    model = AdaptiveSenseModel(
        min_samples=3,
        active_limit=2,
        max_candidates=12,
        relation_window=4,
        exploration_limit=4,
        probe_limit=2,
    )
    available = tuple(f"candidate-{index}" for index in range(10))

    first = model.sampling_plan(available)
    second = model.sampling_plan(available)

    assert not first.active
    assert len(first.probing) == 4
    assert len(second.probing) == 4
    assert set(first.probing).isdisjoint(second.probing)
    assert first.unknown_count == 10


def test_mature_sense_is_routine_while_unknown_and_dormant_senses_rotate() -> None:
    model = AdaptiveSenseModel(
        min_samples=2,
        active_limit=1,
        max_candidates=8,
        relation_window=4,
        exploration_limit=4,
        probe_limit=1,
    )
    model.observe((reading("mature", 1.0, 1), reading("dormant", 1.0, 1)))
    model.observe((reading("mature", 9.0, 2), reading("dormant", 1.0, 2)))

    available = ("mature", "dormant", "unknown-a", "unknown-b")
    plans = [model.sampling_plan(available) for _ in range(4)]

    assert all(plan.active == ("mature",) for plan in plans)
    assert all(len(plan.probing) == 1 for plan in plans)
    probed = {capability_id for plan in plans for capability_id in plan.probing}
    assert {"dormant", "unknown-a", "unknown-b"}.issubset(probed)


def test_sampling_cursor_survives_checkpoint_without_persisting_observations() -> None:
    model = AdaptiveSenseModel(
        min_samples=2,
        active_limit=1,
        max_candidates=8,
        relation_window=4,
        exploration_limit=2,
        probe_limit=1,
    )
    available = ("a", "b", "c", "d")
    first = model.sampling_plan(available)
    payload = model.export()
    restored = AdaptiveSenseModel.restore(payload)
    second = restored.sampling_plan(available)

    assert set(first.probing).isdisjoint(second.probing)
    assert "previous_values" not in payload
