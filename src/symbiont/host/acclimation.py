from __future__ import annotations

import math
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

    Validated at construction (roadmap safety finding A07): a baseline
    restored from an external checkpoint is untrusted input, and a
    negative/non-finite variance or count here does not fail loudly at the
    boundary — it fails later, confusingly, wherever ``stdev`` first gets
    computed (``math domain error`` from a negative square root). Refusing
    it here means a corrupt checkpoint is rejected as a whole at import,
    never partially accepted.
    """

    count: int
    mean: float
    variance: float

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise ValueError("count must be an int")
        if self.count < 0:
            raise ValueError("count must be non-negative")
        if not math.isfinite(self.mean):
            raise ValueError("mean must be finite")
        if not math.isfinite(self.variance) or self.variance < 0.0:
            raise ValueError("variance must be finite and non-negative")

    @property
    def stdev(self) -> float:
        return sqrt(self.variance)


@dataclass(slots=True)
class RunningStats:
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

    @classmethod
    def from_baseline(cls, baseline: CapabilityBaseline) -> "RunningStats":
        """Reconstruct running stats from an already-summarized baseline
        (roadmap v0.37 checkpoints) — never from raw samples, since those
        were never retained in the first place."""
        stats = cls(count=baseline.count, mean=baseline.mean)
        stats._m2 = baseline.variance * baseline.count
        return stats


from ..core.foundation.epistemic import DEFAULT_EPISTEMIC_CONVENTIONS
from ..core.foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()


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

    def __init__(
        self,
        *,
        max_capabilities: int = _DEFAULT_LIMITS.max_capabilities,
        min_samples: int = DEFAULT_EPISTEMIC_CONVENTIONS.established_signal_min_samples,
    ) -> None:
        if max_capabilities < 1:
            raise ValueError("max_capabilities must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self._max_capabilities = max_capabilities
        self._min_samples = min_samples
        self._stats: dict[str, RunningStats] = {}
        self._last_seen: dict[str, int] = {}
        self._tick = 0

    def _evict_for(self, incoming_capability_id: str) -> bool:
        """Retire the least-recently-observed capability to make room for
        one this instance has never seen before (roadmap safety finding
        B02) — mirrors :class:`~symbiont.host.adaptive.AdaptiveSenseModel`'s
        own eviction, applied to acclimation's independent capability cap.
        Without this, once ``max_capabilities`` fills up with capabilities
        that later vanish from the host, no new capability can ever be
        learned again. Never evicts anything just observed this call.
        """
        candidates = [
            capability_id
            for capability_id in self._stats
            if self._last_seen.get(capability_id, 0) < self._tick
        ]
        if not candidates:
            return False
        oldest = min(candidates, key=lambda capability_id: (self._last_seen.get(capability_id, 0), capability_id))
        del self._stats[oldest]
        self._last_seen.pop(oldest, None)
        return True

    def observe(self, readings: Iterable[SensorReading]) -> None:
        self._tick += 1
        for reading in readings:
            if reading.value is None:
                continue  # an unavailable reading carries no signal to learn from
            stats = self._stats.get(reading.capability_id)
            if stats is None:
                if len(self._stats) >= self._max_capabilities and not self._evict_for(reading.capability_id):
                    continue
                stats = RunningStats()
                self._stats[reading.capability_id] = stats
            stats.update(reading.value)
            self._last_seen[reading.capability_id] = self._tick

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

    def restore(self, capability_id: str, baseline: CapabilityBaseline) -> None:
        """Restore a previously-exported baseline (roadmap v0.37 checkpoints).

        Only descriptive statistics are restored — never raw readings, since
        those were never retained in the first place. Subject to the same
        ``max_capabilities`` bound as ``observe``.
        """
        if capability_id not in self._stats and len(self._stats) >= self._max_capabilities:
            return
        self._stats[capability_id] = RunningStats.from_baseline(baseline)

    @property
    def known_capabilities(self) -> tuple[str, ...]:
        """Every capability id ever observed, acclimated or not.

        Unlike ``acclimated_capabilities`` this includes capabilities still
        below ``min_samples`` — useful for a caller (roadmap v0.38's
        attention allocation) that wants to know a capability exists at all
        even before it has enough samples to describe a baseline for it.
        """
        return tuple(sorted(self._stats))

    @property
    def acclimated_capabilities(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                capability_id
                for capability_id, stats in self._stats.items()
                if stats.count >= self._min_samples
            )
        )
