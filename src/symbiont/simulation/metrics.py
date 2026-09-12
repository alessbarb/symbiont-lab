from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .evaluation import CalibrationBin


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def brier_score(decisions: int, sum_squared_errors: float) -> float:
    return sum_squared_errors / decisions if decisions else 0.0


def expected_calibration_error(bins: list[CalibrationBin], total_decisions: int) -> float:
    if not total_decisions:
        return 0.0
    error = 0.0
    for calibration_bin in bins:
        if not calibration_bin.count:
            continue
        avg_probability = calibration_bin.probability_sum / calibration_bin.count
        event_rate = calibration_bin.target_sum / calibration_bin.count
        error += (calibration_bin.count / total_decisions) * abs(avg_probability - event_rate)
    return error
