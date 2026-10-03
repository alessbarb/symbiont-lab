from __future__ import annotations

import pytest

from symbiont.host import (
    CyclePhase,
    Percept,
    ReadingPrivacyClass,
    ReadingQuality,
    RhythmModel,
    Unit,
    cycle_phase_for_tick,
    learn_local_host_rhythms,
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
    ("tick", "expected"),
    [
        (0, CyclePhase.PHASE_0),
        (511, CyclePhase.PHASE_0),
        (512, CyclePhase.PHASE_1),
        (1024, CyclePhase.PHASE_2),
        (2047, CyclePhase.PHASE_3),
        (2048, CyclePhase.PHASE_0),
    ],
)
def test_internal_cycle_phase_follows_causal_tick(tick, expected):
    # ADR-0042: phase derives from the organism's own tick, never the OS clock.
    assert cycle_phase_for_tick(tick) == expected


@pytest.mark.parametrize(("tick", "period"), [(-1, 2048), (0, 3)])
def test_internal_cycle_phase_rejects_invalid_input(tick, period):
    with pytest.raises(ValueError):
        cycle_phase_for_tick(tick, period)


def test_phase_values_carry_no_time_of_day_semantics():
    for phase in CyclePhase:
        assert phase.value.startswith("phase.")


def test_not_learned_before_min_samples():
    model = RhythmModel(min_samples=3)
    model.observe([_percept("system_load", 0.5)], phase=CyclePhase.PHASE_0)

    assert not model.is_learned("system_load", CyclePhase.PHASE_0)
    assert model.baseline("system_load", CyclePhase.PHASE_0) is None


def test_learned_once_min_samples_reached_per_phase():
    model = RhythmModel(min_samples=2)
    model.observe([_percept("system_load", 0.2)], phase=CyclePhase.PHASE_0)
    model.observe([_percept("system_load", 0.4)], phase=CyclePhase.PHASE_0)

    assert model.is_learned("system_load", CyclePhase.PHASE_0)
    baseline = model.baseline("system_load", CyclePhase.PHASE_0)
    assert baseline.count == 2
    assert baseline.mean == pytest.approx(0.3)


def test_phases_are_tracked_independently():
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", 0.1)], phase=CyclePhase.PHASE_0)
    model.observe([_percept("system_load", 0.9)], phase=CyclePhase.PHASE_2)

    assert model.baseline("system_load", CyclePhase.PHASE_0).mean == pytest.approx(0.1)
    assert model.baseline("system_load", CyclePhase.PHASE_2).mean == pytest.approx(0.9)
    assert model.baseline("system_load", CyclePhase.PHASE_1) is None


def test_co_occurring_percepts_reflects_what_was_observed_together():
    model = RhythmModel(min_samples=1)
    model.observe(
        [_percept("system_load", 0.5), _percept("storage_pressure", 80.0)],
        phase=CyclePhase.PHASE_3,
    )

    assert model.co_occurring_percepts(CyclePhase.PHASE_3) == ("storage_pressure", "system_load")
    assert model.co_occurring_percepts(CyclePhase.PHASE_0) == ()


def test_unavailable_percepts_are_not_observed():
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", None)], phase=CyclePhase.PHASE_0)

    assert not model.is_learned("system_load", CyclePhase.PHASE_0)


def test_context_count_is_bounded():
    model = RhythmModel(max_contexts=1, min_samples=1)
    model.observe([_percept("a", 1.0), _percept("b", 1.0)], phase=CyclePhase.PHASE_0)

    assert len(model.learned_contexts) == 1


@pytest.mark.parametrize("kwargs", [{"max_contexts": 0}, {"min_samples": 0}])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RhythmModel(**kwargs)


def test_baseline_exposes_no_classification_surface():
    """Same guarantee as v0.33's HostAcclimation: this can only ever produce
    descriptive stats, never a verdict."""
    model = RhythmModel(min_samples=1)
    model.observe([_percept("system_load", 0.5)], phase=CyclePhase.PHASE_0)
    baseline = model.baseline("system_load", CyclePhase.PHASE_0)

    public_attrs = {name for name in dir(baseline) if not name.startswith("_")}
    assert public_attrs <= {"count", "mean", "variance", "stdev"}


def test_learn_local_host_rhythms_seeds_a_real_model():
    model = learn_local_host_rhythms(ticks=5)

    assert model.learned_contexts
    assert model.co_occurring_percepts(CyclePhase.PHASE_0)


def test_learn_local_host_rhythms_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        learn_local_host_rhythms(ticks=0)
