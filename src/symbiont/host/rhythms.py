from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .acclimation import CapabilityBaseline, RunningStats
from .percepts import Percept


class TimeBucket(StrEnum):
    """A coarse, cyclical phase of day — never an exact hour, timestamp or
    calendar date. Four buckets repeat every day forever; nothing here can
    identify *which* day it was, only roughly what part of a day it was."""

    NIGHT = "night"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


def time_bucket_for_hour(hour: int) -> TimeBucket:
    """Quantize an hour-of-day (0-23) into one of four coarse buckets.

    The caller passes a raw hour only to compute this bucket; nothing here
    stores or returns the hour itself. This is the privacy boundary for
    "time-of-day" context (roadmap v0.35): everything downstream of this
    function only ever sees the bucket.
    """
    if not 0 <= hour <= 23:
        raise ValueError("hour must be between 0 and 23")
    if hour < 6:
        return TimeBucket.NIGHT
    if hour < 12:
        return TimeBucket.MORNING
    if hour < 18:
        return TimeBucket.AFTERNOON
    return TimeBucket.EVENING


@dataclass(slots=True, frozen=True)
class _ContextKey:
    percept_name: str
    time_bucket: TimeBucket


class RhythmModel:
    """Learn per-time-bucket baselines and co-occurrence for named percepts
    (roadmap v0.35).

    Extends v0.33's single global baseline per capability
    (:class:`~symbiont.host.acclimation.HostAcclimation`) into one baseline
    per (percept name, time-of-day bucket) pair — e.g. "system_load tends
    to run lower at night than in the afternoon" — without ever storing a
    specific timestamp or calendar date, only a coarse, cyclical
    :class:`TimeBucket`. Threat classification remains out of scope, the
    same as v0.33's acclimation: this can only ever produce descriptive
    statistics and a list of percept names, never a verdict.

    Bounded: tracks at most ``max_contexts`` distinct (percept, bucket)
    pairs; anything beyond that is silently dropped rather than growing
    state without bound.
    """

    def __init__(self, *, max_contexts: int = 256, min_samples: int = 5) -> None:
        if max_contexts < 1:
            raise ValueError("max_contexts must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self._max_contexts = max_contexts
        self._min_samples = min_samples
        self._stats: dict[_ContextKey, RunningStats] = {}

    def observe(self, percepts: Iterable[Percept], *, time_bucket: TimeBucket) -> None:
        for percept in percepts:
            if percept.value is None:
                continue
            key = _ContextKey(percept.name, time_bucket)
            stats = self._stats.get(key)
            if stats is None:
                if len(self._stats) >= self._max_contexts:
                    continue
                stats = RunningStats()
                self._stats[key] = stats
            stats.update(percept.value)

    def restore(
        self, percept_name: str, time_bucket: TimeBucket, baseline: CapabilityBaseline
    ) -> None:
        """Restore a previously-exported per-context baseline (roadmap v0.37
        checkpoints). Only descriptive statistics are restored — never raw
        readings. Subject to the same ``max_contexts`` bound as ``observe``.
        """
        key = _ContextKey(percept_name, time_bucket)
        if key not in self._stats and len(self._stats) >= self._max_contexts:
            return
        self._stats[key] = RunningStats.from_baseline(baseline)

    def is_learned(self, percept_name: str, time_bucket: TimeBucket) -> bool:
        stats = self._stats.get(_ContextKey(percept_name, time_bucket))
        return stats is not None and stats.count >= self._min_samples

    def baseline(self, percept_name: str, time_bucket: TimeBucket) -> CapabilityBaseline | None:
        """The learned per-bucket baseline, or ``None`` before enough samples exist."""
        stats = self._stats.get(_ContextKey(percept_name, time_bucket))
        if stats is None or stats.count < self._min_samples:
            return None
        return stats.snapshot()

    def co_occurring_percepts(self, time_bucket: TimeBucket) -> tuple[str, ...]:
        """Percept names ever observed together within this time bucket."""
        return tuple(
            sorted(
                key.percept_name
                for key in self._stats
                if key.time_bucket == time_bucket
            )
        )

    @property
    def learned_contexts(self) -> tuple[tuple[str, TimeBucket], ...]:
        return tuple(
            sorted(
                (key.percept_name, key.time_bucket)
                for key, stats in self._stats.items()
                if stats.count >= self._min_samples
            )
        )
