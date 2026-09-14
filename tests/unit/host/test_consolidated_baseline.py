from __future__ import annotations

import pytest

from symbiont.host.acclimation import CapabilityBaseline
from symbiont.host.consolidated_baseline import (
    consolidate_baseline,
    maturity_class_from_observation_support,
    seed_capability_baseline,
)


def test_maturity_class_from_observation_support_is_monotone_and_coarse():
    assert maturity_class_from_observation_support(0) == 0
    assert maturity_class_from_observation_support(1) == 1
    assert maturity_class_from_observation_support(1000) == 7
    classes = [maturity_class_from_observation_support(n) for n in range(0, 300, 3)]
    assert classes == sorted(classes)


def test_constant_signal_gets_the_constant_scale_sentinel():
    baseline = CapabilityBaseline(count=50, mean=700.0, variance=0.0)
    seed = consolidate_baseline(baseline)
    assert seed.scale_class == 0

    restored = seed_capability_baseline(seed)
    assert restored.variance == pytest.approx(0.0)
    assert restored.mean == pytest.approx(700.0, rel=0.15)


def test_high_mean_low_variance_signal_does_not_saturate_center():
    moderate = consolidate_baseline(CapabilityBaseline(count=20, mean=1000.0, variance=25.0))
    extreme = consolidate_baseline(CapabilityBaseline(count=20, mean=1_000_000_000.0, variance=25.0))
    assert moderate.center_class != extreme.center_class


def test_center_and_scale_round_trip_approximately_and_never_fabricate_count():
    baseline = CapabilityBaseline(count=123, mean=517.4, variance=63.2 * 63.2)
    seed = consolidate_baseline(baseline)
    restored = seed_capability_baseline(seed)

    # 32 classes over a 12-decade signed-log range means each bin spans
    # roughly a factor of 1.5x in the reconstructed magnitude -- this is a
    # coarse order-of-magnitude anchor by design, not a precise estimate.
    assert restored.mean == pytest.approx(517.4, rel=0.6)
    assert restored.stdev == pytest.approx(63.2, rel=0.6)
    assert restored.count <= 8
    assert restored.count != 123


def test_two_baselines_one_ordinary_observation_apart_are_not_differenced_to_the_same_precision():
    before = consolidate_baseline(CapabilityBaseline(count=100, mean=50.0, variance=4.0))
    after = consolidate_baseline(CapabilityBaseline(count=101, mean=50.0049, variance=4.0))
    assert before == after
