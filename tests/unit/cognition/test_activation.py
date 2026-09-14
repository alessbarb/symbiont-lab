from __future__ import annotations

import math

import pytest

from symbiont.cognition.activation import SensoryNormalizer


def test_cold_start_does_not_divide_by_zero():
    normalizer = SensoryNormalizer()
    result = normalizer.normalize(5.0)
    assert math.isfinite(result)


def test_output_is_always_bounded_by_tanh():
    normalizer = SensoryNormalizer()
    for value in [0.0, 1.0, 1.0, 1.0, 1.0, 1000000.0, -1000000.0]:
        result = normalizer.normalize(value)
        assert -1.0 < result < 1.0


def test_repeated_identical_values_converge_toward_zero_activation():
    normalizer = SensoryNormalizer()
    last = None
    for _ in range(50):
        last = normalizer.normalize(3.0)
    assert abs(last) < 0.05


def test_a_fresh_outlier_after_a_stable_baseline_produces_a_large_magnitude():
    normalizer = SensoryNormalizer()
    for _ in range(30):
        normalizer.normalize(1.0)
    outlier = normalizer.normalize(1000.0)
    assert abs(outlier) > 0.5


def test_z_score_clipping_bounds_extreme_outliers_consistently():
    normalizer = SensoryNormalizer()
    for _ in range(30):
        normalizer.normalize(1.0)
    huge = normalizer.normalize(1e9)
    normalizer2 = SensoryNormalizer()
    for _ in range(30):
        normalizer2.normalize(1.0)
    bigger = normalizer2.normalize(1e12)
    assert huge == pytest.approx(bigger, abs=1e-6)
