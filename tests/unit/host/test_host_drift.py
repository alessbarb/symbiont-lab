from __future__ import annotations

import pytest

from symbiont.host.drift import DriftAwareBaseline, DriftKind


def _seed(baseline: DriftAwareBaseline, values) -> None:
    for value in values:
        baseline.observe(value)


def test_not_established_before_min_samples_yields_none():
    baseline = DriftAwareBaseline(min_samples=5)
    obs = baseline.observe(1.0)

    assert not baseline.is_established
    assert obs.kind == DriftKind.NONE
    assert obs.z_score is None


def test_established_after_min_samples():
    baseline = DriftAwareBaseline(min_samples=3)
    _seed(baseline, [1.0, 1.0])

    assert not baseline.is_established
    baseline.observe(1.0)
    assert baseline.is_established


def test_ordinary_values_classify_as_none():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    obs = baseline.observe(1.01)
    assert obs.kind == DriftKind.NONE


def test_single_large_outlier_is_isolated_and_does_not_move_baseline():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])
    mean_before = baseline.mean
    stdev_before = baseline.stdev

    obs = baseline.observe(10.0)

    assert obs.kind == DriftKind.ISOLATED
    assert baseline.mean == pytest.approx(mean_before)
    assert baseline.stdev == pytest.approx(stdev_before)


def test_isolated_spike_then_revert_returns_to_none():
    """A spike followed by reverts to the pre-spike level must not falsely
    confirm a regime shift back to "normal" — see drift.py's design note."""
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    assert baseline.observe(10.0).kind == DriftKind.ISOLATED
    kinds = [baseline.observe(1.0).kind for _ in range(5)]

    assert DriftKind.REGIME_SHIFT not in kinds
    assert kinds[-1] == DriftKind.NONE
    assert baseline.mean == pytest.approx(1.0, abs=0.05)


def test_sustained_shift_confirms_as_regime_shift_after_run_length():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    kinds = [baseline.observe(5.0).kind for _ in range(3)]

    assert kinds[-1] == DriftKind.REGIME_SHIFT
    assert kinds[0] != DriftKind.NONE
    assert baseline.mean == pytest.approx(5.0)
    assert baseline.stdev == pytest.approx(0.0)


def test_regime_shift_rebaselines_so_next_value_reads_as_normal():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])
    for _ in range(3):
        baseline.observe(5.0)

    assert baseline.observe(5.0).kind == DriftKind.NONE


def test_broken_streak_before_confirmation_does_not_move_baseline():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])
    mean_before = baseline.mean

    baseline.observe(5.0)
    baseline.observe(5.0)
    baseline.observe(1.0)  # streak breaks before regime_run is reached

    assert baseline.mean == pytest.approx(mean_before, abs=0.05)
    assert baseline.mean != pytest.approx(5.0)


def test_alternating_direction_never_confirms_a_regime_shift():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    _seed(baseline, [1.0, 1.05, 0.95, 1.02, 0.98])

    kinds = []
    for value in [5.0, -3.0, 5.0, -3.0, 5.0, -3.0]:
        kinds.append(baseline.observe(value).kind)

    assert DriftKind.REGIME_SHIFT not in kinds


def test_zero_variance_baseline_treats_any_change_as_infinite_z():
    baseline = DriftAwareBaseline(min_samples=3)
    _seed(baseline, [1.0, 1.0, 1.0])

    obs = baseline.observe(1.0)
    assert obs.z_score == 0.0

    obs = baseline.observe(2.0)
    assert obs.z_score == float("inf")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"decay": 0.0},
        {"decay": 1.5},
        {"isolated_z": 0.0},
        {"regime_z": 0.0},
        {"isolated_z": 1.0, "regime_z": 2.0},
        {"regime_run": 0},
        {"min_samples": 0},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        DriftAwareBaseline(**kwargs)


def test_observation_exposes_no_classification_surface():
    """Same discipline as v0.33/v0.35: only descriptive/statistical fields,
    never a threat or security verdict."""
    baseline = DriftAwareBaseline(min_samples=1)
    obs = baseline.observe(1.0)

    public_attrs = {name for name in dir(obs) if not name.startswith("_")}
    assert public_attrs <= {"kind", "z_score"}
