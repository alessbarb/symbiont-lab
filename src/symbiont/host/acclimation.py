from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Iterable

from .readings import SensorReading


@dataclass(slots=True, frozen=True)
class CapabilityBaseline:
    """Purely descriptive running statistics for one capability's real readings.

    Deliberately exposes only mean, spread and sample count — nothing that
    could function as a deviation, novelty or anomaly signal. That kind of
    judgment is explicitly out of scope for acclimation (roadmap v0.33);
    "drift-aware beliefs" (v0.36) is where distinguishing novelty from
    gradual change belongs, once cognition can reason about it deliberately
    rather than a perception-layer helper doing it as a side effect.
    """

    count: int
    mean: float
    variance: float

    @property
    def stdev(self) -> float:
        return sqrt(self.variance)


@dataclass(slots=True)
class _RunningStats:
    """Welford's algorithm: O(1) memory per capability, no raw sample history."""

    count: int = 0
    mean: float = 0.0
    _m2: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self._m2 += delta * (value - self.mean)

    def snapshot(self) -> CapabilityBaseline:
        variance = self._m2 / self.count if self.count > 1 else 0.0
        return CapabilityBaseline(count=self.count, mean=self.mean, variance=variance)


class HostAcclimation:
    """Learn an initial per-capability baseline from real readings (roadmap v0.33).

    Withholds any threat conclusion by construction: the only things this
    class can produce are ``CapabilityBaseline`` (mean/stdev/count) and a
    boolean "have I seen enough samples yet" — there is no method here that
    could be read as a classification, a risk score or an anomaly flag.

    Bounded: tracks at most ``max_capabilities`` distinct capability ids; a
    reading for a capability beyond that limit is silently dropped rather
    than growing state without bound.
    """

    def __init__(self, *, max_capabilities: int = 64, min_samples: int = 5) -> None:
        if max_capabilities < 1:
            raise ValueError("max_capabilities must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self._max_capabilities = max_capabilities
        self._min_samples = min_samples
        self._stats: dict[str, _RunningStats] = {}

    def observe(self, readings: Iterable[SensorReading]) -> None:
        for reading in readings:
            if reading.value is None:
                continue  # an unavailable reading carries no signal to learn from
            stats = self._stats.get(reading.capability_id)
            if stats is None:
                if len(self._stats) >= self._max_capabilities:
                    continue
                stats = _RunningStats()
                self._stats[reading.capability_id] = stats
            stats.update(reading.value)

    def is_acclimated(self, capability_id: str) -> bool:
        stats = self._stats.get(capability_id)
        return stats is not None and stats.count >= self._min_samples

    def baseline(self, capability_id: str) -> CapabilityBaseline | None:
        """The learned baseline, or ``None`` before enough samples exist.

        Returning ``None`` pre-acclimation (rather than a baseline built
        from too few samples) is itself part of withholding conclusions
        early — a mean of one or two points is not something to act on.
        """
        stats = self._stats.get(capability_id)
        if stats is None or stats.count < self._min_samples:
            return None
        return stats.snapshot()

    @property
    def acclimated_capabilities(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                capability_id
                for capability_id, stats in self._stats.items()
                if stats.count >= self._min_samples
            )
        )
