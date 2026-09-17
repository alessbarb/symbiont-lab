"""Shared coarse-class codec for HostAcclimation/RhythmModel/DriftAwareBaseline
statistics (design docs/design/biological-memory-consolidation.md §10.2, §16).

center_class is a signed-log encoding of the mean's own magnitude -- never
mean/stdev, which divides by zero at stdev==0 and saturates whenever
|mean| >> stdev (owner-rejected failure mode, 2026-09-14). scale_class is a
CONSTANT sentinel plus log-scale buckets of stdev. Restoring seeds a small,
fixed, maturity-scaled prior weight as the synthetic count -- never the real
historical sample count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .acclimation import CapabilityBaseline

from ..core.epistemic import DEFAULT_EPISTEMIC_CONVENTIONS

_CENTER_CLASSES = 32
_CENTER_LOG_RANGE = (-6.0, 6.0)
_SCALE_LOG_CLASSES = 16
_SCALE_LOG_RANGE = (-6.0, 6.0)
_SCALE_EPSILON = 1e-9
_MATURITY_THRESHOLDS = DEFAULT_EPISTEMIC_CONVENTIONS.maturity_thresholds
_PRIOR_WEIGHTS_BY_MATURITY = (1, 1, 2, 3, 4, 6, 8, 8)


def _quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int:
    low, high = bounds
    clipped = max(low, min(high, value))
    ratio = (clipped - low) / (high - low)
    return round(ratio * (num_classes - 1))


def _dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float:
    low, high = bounds
    ratio = class_id / (num_classes - 1)
    return low + ratio * (high - low)


def maturity_class_from_observation_support(count: int) -> int:
    """Coarse, monotone class over a real sample count -- distinctly named
    from PR1's maturity_class_from_support_epochs even though both delegate
    to the same threshold shape, since count and epoch-count are different
    magnitudes."""
    if count < 0:
        count = 0
    matured_class = 0
    for index, threshold in enumerate(_MATURITY_THRESHOLDS):
        if count >= threshold:
            matured_class = index
    return matured_class


def _center_class(mean: float) -> int:
    magnitude = math.log10(1.0 + abs(mean))
    signed = math.copysign(magnitude, mean) if mean != 0 else 0.0
    return _quantize_signed(signed, _CENTER_LOG_RANGE, _CENTER_CLASSES)


def _center_representative(cls: int) -> float:
    signed = _dequantize_signed(cls, _CENTER_LOG_RANGE, _CENTER_CLASSES)
    magnitude = 10.0**abs(signed) - 1.0
    return math.copysign(magnitude, signed) if signed != 0 else 0.0


def _scale_class(stdev: float) -> int:
    if stdev <= _SCALE_EPSILON:
        return 0
    exponent = math.log10(stdev)
    return 1 + _quantize_signed(exponent, _SCALE_LOG_RANGE, _SCALE_LOG_CLASSES)


def _scale_representative(cls: int) -> float:
    if cls == 0:
        return 0.0
    exponent = _dequantize_signed(cls - 1, _SCALE_LOG_RANGE, _SCALE_LOG_CLASSES)
    return 10.0**exponent


@dataclass(slots=True, frozen=True)
class ConsolidatedBaselineSeed:
    center_class: int
    scale_class: int
    maturity_class: int


def consolidate_baseline(baseline: CapabilityBaseline) -> ConsolidatedBaselineSeed:
    return ConsolidatedBaselineSeed(
        center_class=_center_class(baseline.mean),
        scale_class=_scale_class(baseline.stdev),
        maturity_class=maturity_class_from_observation_support(baseline.count),
    )


def seed_capability_baseline(seed: ConsolidatedBaselineSeed) -> CapabilityBaseline:
    stdev = _scale_representative(seed.scale_class)
    mean = _center_representative(seed.center_class)
    weight = _PRIOR_WEIGHTS_BY_MATURITY[seed.maturity_class]
    return CapabilityBaseline(count=weight, mean=mean, variance=stdev * stdev)
