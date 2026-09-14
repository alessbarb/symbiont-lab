import pytest

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


# --- A02: export withholds under-sampled aggregates (privacy) ---


def test_export_withholds_a_state_below_min_samples() -> None:
    model = AdaptiveSenseModel(min_samples=4)
    model.observe((reading("a", 123.25, 1),))

    payload = model.export()

    assert payload["states"] == []


def test_export_includes_a_state_once_min_samples_reached() -> None:
    model = AdaptiveSenseModel(min_samples=2)
    model.observe((reading("a", 1.0, 1),))
    model.observe((reading("a", 2.0, 2),))

    payload = model.export()

    assert len(payload["states"]) == 1
    assert payload["states"][0]["available_samples"] == 2


def test_export_withholds_a_relation_below_min_relation_samples() -> None:
    model = AdaptiveSenseModel(min_samples=1, min_relation_samples=3)
    model.observe((reading("a", 1.0, 1), reading("b", 2.0, 1)))

    payload = model.export()

    assert payload["relations"] == []


def test_export_includes_a_relation_once_min_relation_samples_reached() -> None:
    model = AdaptiveSenseModel(min_samples=1, min_relation_samples=3)
    for tick in range(3):
        model.observe((reading("a", float(tick), tick), reading("b", float(tick * 2), tick)))

    payload = model.export()

    assert len(payload["relations"]) == 1


# --- A04: bounded capacity evicts stale entries instead of blocking forever ---


def test_new_candidate_is_learned_after_old_ones_vanish_at_capacity() -> None:
    model = AdaptiveSenseModel(min_samples=1, active_limit=4, max_candidates=4, relation_window=4, exploration_limit=4, probe_limit=4)
    for tick in range(4):
        model.observe((reading(f"old-{i}", float(i), tick) for i in range(4)))

    for tick in range(4, 8):
        model.observe((reading("new-signal", 1.0, tick),))

    assert any(state.capability_id == "new-signal" for state in model.states)
    assert len(model.states) <= 4


def test_capacity_eviction_never_removes_something_seen_this_tick() -> None:
    model = AdaptiveSenseModel(min_samples=1, active_limit=2, max_candidates=2, relation_window=2, exploration_limit=2, probe_limit=2)
    model.observe((reading("a", 1.0, 1), reading("b", 1.0, 1)))
    # A single batch introducing two brand-new ids at once must not evict
    # either of the two just observed in the same call.
    model.observe((reading("c", 1.0, 2), reading("d", 1.0, 2)))

    ids = {state.capability_id for state in model.states}
    assert ids == {"c", "d"}


def test_stale_relations_are_dropped_when_their_state_is_evicted() -> None:
    model = AdaptiveSenseModel(min_samples=1, active_limit=2, max_candidates=2, relation_window=2, min_relation_samples=3, exploration_limit=2, probe_limit=2)
    model.observe((reading("a", 1.0, 1), reading("b", 1.0, 1)))
    model.observe((reading("a", 2.0, 2), reading("b", 2.0, 2)))
    assert model._relations  # a<->b relation exists internally

    model.observe((reading("c", 1.0, 3),))
    model.observe((reading("d", 1.0, 4),))

    assert not any("a" in key or "b" in key for key in model._relations)


def test_new_relation_pair_is_learned_after_old_relations_fill_capacity() -> None:
    model = AdaptiveSenseModel(min_samples=1, max_candidates=64, relation_window=32, max_relations=4, min_relation_samples=3)
    for group in range(2):
        model.observe([reading(f"g{group}-{i}", float(i), group) for i in range(4)])
    assert len(model._relations) == 4

    for tick in range(10, 13):
        model.observe((reading("late-a", float(tick), tick), reading("late-b", float(tick * 2), tick)))

    learned = any(
        {relation.capability_a, relation.capability_b} == {"late-a", "late-b"}
        for relation in model._relations.values()
    )
    assert learned
    assert len(model._relations) <= 4


# --- A06: correlation is stable under large offsets (numerical precision) ---


def test_correlation_is_invariant_to_a_large_shared_offset() -> None:
    from symbiont.host.adaptive import PairAccumulator

    baseline = PairAccumulator()
    shifted = PairAccumulator()
    for i in range(100):
        baseline.observe(i, 2 * i)
        shifted.observe(10**10 + i, 10**10 + 2 * i)

    assert baseline.correlation == pytest.approx(1.0)
    assert shifted.correlation == pytest.approx(1.0)
