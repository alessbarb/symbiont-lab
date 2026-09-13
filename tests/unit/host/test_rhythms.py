from __future__ import annotations

import pytest

from symbiont.host import (
    Percept,
    ReadingPrivacyClass,
    ReadingQuality,
    RhythmModel,
    TimeBucket,
    Unit,
    learn_local_host_rhythms,
    time_bucket_for_hour,
)


def _percept(name: str, value: float | None) -> Percept:
    return Percept(
        name=name,
        value=value,
        unit=Unit.RATIO,
        quality=ReadingQuality.NOMINAL if value is not None else ReadingQuality.UNAVAILABLE,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (0, TimeBucket.NIGHT),
        (5, TimeBucket.NIGHT),
        (6, TimeBucket.MORNING),
        (11, TimeBucket.MORNING),
        (12, TimeBucket.AFTERNOON),
        (17, TimeBucket.AFTERNOON),
        (18, TimeBucket.EVENING),
        (23, TimeBucket.EVENING),
    ],
)
def test_time_bucket_boundaries(hour, expected):
    assert time_bucket_for_hour(hour) == expected


@pytest.mark.parametrize("hour", [-1, 24, 100])
def test_time_bucket_rejects_out_of_range_hour(hour):
    with pytest.raises(ValueError):
        time_bucket_for_hour(hour)


def test_not_learned_before_min_samples():
    model = RhythmModel(min_samples=3)
    model.observe([_percept("system_load", 0.5)], time_bucket=TimeBucket.NIGHT)

    assert not model.is_learned("system_load", TimeBucket.NIGHT)
    assert model.baseline("system_load", TimeBucket.NIGHT) is None


def test_learned_once_min_samples_reached_per_bucket():
    model = RhythmModel(min_samples=2)
    model.observe([_percept("system_load", 0.2)], time_bucket=TimeBucket.NIGHT)
    model.observe([_percept("system_load", 0.4)], time_bucket=TimeBucket.NIGHT)

    assert model.is_learned("system_load", TimeBucket.NIGHT)
    baseline = model.baseline("system_load", TimeBucket.NIGHT)
    assert baseline.count == 2
    assert baseline.mean == pytest.approx(0.3)


def test_buckets_are_tracked_independently():
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", 0.1)], time_bucket=TimeBucket.NIGHT)
    model.observe([_percept("system_load", 0.9)], time_bucket=TimeBucket.AFTERNOON)

    assert model.baseline("system_load", TimeBucket.NIGHT).mean == pytest.approx(0.1)
    assert model.baseline("system_load", TimeBucket.AFTERNOON).mean == pytest.approx(0.9)
    assert model.baseline("system_load", TimeBucket.MORNING) is None


def test_co_occurring_percepts_reflects_what_was_observed_together():
    model = RhythmModel(min_samples=1)
    model.observe(
        [_percept("system_load", 0.5), _percept("storage_pressure", 80.0)],
        time_bucket=TimeBucket.EVENING,
    )

    assert model.co_occurring_percepts(TimeBucket.EVENING) == ("storage_pressure", "system_load")
    assert model.co_occurring_percepts(TimeBucket.NIGHT) == ()


def test_unavailable_percepts_are_not_observed():
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", None)], time_bucket=TimeBucket.NIGHT)

    assert not model.is_learned("system_load", TimeBucket.NIGHT)


def test_context_count_is_bounded():
    model = RhythmModel(max_contexts=1, min_samples=1)
    model.observe([_percept("a", 1.0), _percept("b", 1.0)], time_bucket=TimeBucket.NIGHT)

    assert len(model.learned_contexts) == 1


@pytest.mark.parametrize("kwargs", [{"max_contexts": 0}, {"min_samples": 0}])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RhythmModel(**kwargs)


def test_baseline_exposes_no_classification_surface():
    """Same guarantee as v0.33's HostAcclimation: this can only ever produce
    descriptive stats, never a verdict."""
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", 0.5)], time_bucket=TimeBucket.NIGHT)
    baseline = model.baseline("system_load", TimeBucket.NIGHT)

    public_attrs = {name for name in dir(baseline) if not name.startswith("_")}
    assert public_attrs <= {"count", "mean", "variance", "stdev"}


def test_learn_local_host_rhythms_seeds_a_real_model():
    model = learn_local_host_rhythms(ticks=5, time_bucket=TimeBucket.NIGHT)

    assert model.learned_contexts
    assert model.co_occurring_percepts(TimeBucket.NIGHT)


def test_learn_local_host_rhythms_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        learn_local_host_rhythms(ticks=0)
