from __future__ import annotations

from collections.abc import Iterable
import math
import statistics


def safe_mean(values: Iterable[float | None]) -> float | None:
    valid = [v for v in values if v is not None]
    return statistics.mean(valid) if valid else None


def paired_deltas(
    treatment: list[float | None],
    baseline: list[float | None],
) -> list[float]:
    deltas = []
    for t, b in zip(treatment, baseline):
        if t is not None and b is not None:
            deltas.append(t - b)
    return deltas


def mean_delta(
    treatment: list[float | None],
    baseline: list[float | None],
) -> float | None:
    deltas = paired_deltas(treatment, baseline)
    return statistics.mean(deltas) if deltas else None


def aggregate_metric(values: list[float | None]) -> dict[str, float | None]:
    valid = [v for v in values if v is not None]
    if not valid:
        return {"mean": None, "median": None, "std": None, "count": 0}
    return {
        "mean": statistics.mean(valid),
        "median": statistics.median(valid),
        "std": statistics.stdev(valid) if len(valid) > 1 else 0.0,
        "count": len(valid),
    }
