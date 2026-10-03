from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable

from .acclimation import CapabilityBaseline, RunningStats
from .percepts import Percept

# ADR-0042 / ADR-0032: the organism's rhythm context is an internal cyclic
# phase derived from its own persisted causal tick, never the OS clock. Four
# neutral quadrants of one macro cycle; the period is a provisional
# constitution constant that may later be entrained endogenously.
CYCLE_PERIOD_TICKS = 2048
_PHASE_COUNT = 4


class CyclePhase(StrEnum):
    """One quadrant of the organism's internal macro cycle. Carries no
    time-of-day, calendar or host-clock meaning."""

    PHASE_0 = "phase.0"
    PHASE_1 = "phase.1"
    PHASE_2 = "phase.2"
    PHASE_3 = "phase.3"


_PHASES = tuple(CyclePhase)


def cycle_phase_for_tick(tick: int, period: int = CYCLE_PERIOD_TICKS) -> CyclePhase:
    """Deterministic macro phase of a causal tick."""
    if tick < 0:
        raise ValueError("tick must be non-negative")
    if period < _PHASE_COUNT:
        raise ValueError("period must cover every phase")
    return _PHASES[(tick % period) * _PHASE_COUNT // period]


@dataclass(slots=True, frozen=True)
class _ContextKey:
    percept_name: str
    phase: CyclePhase


from ..core.foundation.epistemic import DEFAULT_EPISTEMIC_CONVENTIONS
from ..core.foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()


class RhythmModel:
    """Learn per-phase baselines and co-occurrence for named percepts
    (roadmap v0.35; internal phase since ADR-0042).

    Extends v0.33's single global baseline per capability
    (:class:`~symbiont.host.acclimation.HostAcclimation`) into one baseline
    per (percept name, :class:`CyclePhase`) pair of the organism's internal
    macro cycle. Recurring environmental structure may align with that cycle;
    the host clock never defines it. Threat classification remains out of
    scope: this only ever produces descriptive statistics and percept names.

    Bounded: tracks at most ``max_contexts`` distinct (percept, phase)
    pairs; anything beyond that is silently dropped rather than growing
    state without bound.
    """

    def __init__(
        self,
        *,
        max_contexts: int = _DEFAULT_LIMITS.max_rhythm_contexts,
        min_samples: int = DEFAULT_EPISTEMIC_CONVENTIONS.established_signal_min_samples,
    ) -> None:
        if max_contexts < 1:
            raise ValueError("max_contexts must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self._max_contexts = max_contexts
        self._min_samples = min_samples
        self._stats: dict[_ContextKey, RunningStats] = {}

    def observe(self, percepts: Iterable[Percept], *, phase: CyclePhase) -> None:
        for percept in percepts:
            if percept.value is None:
                continue
            key = _ContextKey(percept.name, phase)
            stats = self._stats.get(key)
            if stats is None:
                if len(self._stats) >= self._max_contexts:
                    continue
                stats = RunningStats()
                self._stats[key] = stats
            stats.update(percept.value)

    def restore(self, percept_name: str, phase: CyclePhase, baseline: CapabilityBaseline) -> None:
        """Restore a previously-exported per-context baseline (roadmap v0.37
        checkpoints). Only descriptive statistics are restored — never raw
        readings. Subject to the same ``max_contexts`` bound as ``observe``.
        """
        key = _ContextKey(percept_name, phase)
        if key not in self._stats and len(self._stats) >= self._max_contexts:
            return
        self._stats[key] = RunningStats.from_baseline(baseline)

    def replay_state(self) -> dict[str, Any]:
        """Return bounded running state needed for deterministic continuation."""
        return {
            "stats": [
                {
                    "percept_name": key.percept_name,
                    "phase": key.phase.value,
                    "count": stats.count,
                    "mean": stats.mean,
                    "m2": stats._m2,
                }
                for key, stats in self._stats.items()
            ]
        }

    def restore_replay_state(self, payload: dict[str, Any]) -> None:
        """Restore the exact bounded per-context accumulators."""
        entries = payload.get("stats", [])
        if not isinstance(entries, list) or len(entries) > self._max_contexts:
            raise ValueError("rhythm replay state exceeds context bound")
        restored: dict[_ContextKey, RunningStats] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("rhythm replay entry is invalid")
            try:
                key = _ContextKey(str(entry["percept_name"]), CyclePhase(entry["phase"]))
                count = entry["count"]
                mean = float(entry["mean"])
                m2 = float(entry["m2"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("rhythm replay entry is invalid") from exc
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
                or not all(map(lambda value: math.isfinite(value), (mean, m2)))
                or m2 < 0.0
            ):
                raise ValueError("rhythm replay numeric state is invalid")
            restored[key] = RunningStats(count=count, mean=mean, _m2=m2)
        self._stats = restored

    def is_learned(self, percept_name: str, phase: CyclePhase) -> bool:
        stats = self._stats.get(_ContextKey(percept_name, phase))
        return stats is not None and stats.count >= self._min_samples

    def baseline(self, percept_name: str, phase: CyclePhase) -> CapabilityBaseline | None:
        """The learned per-phase baseline, or ``None`` before enough samples exist."""
        stats = self._stats.get(_ContextKey(percept_name, phase))
        if stats is None or stats.count < self._min_samples:
            return None
        return stats.snapshot()

    def co_occurring_percepts(self, phase: CyclePhase) -> tuple[str, ...]:
        """Percept names ever observed together within this phase."""
        return tuple(sorted(key.percept_name for key in self._stats if key.phase == phase))

    @property
    def learned_contexts(self) -> tuple[tuple[str, CyclePhase], ...]:
        return tuple(
            sorted(
                (key.percept_name, key.phase)
                for key, stats in self._stats.items()
                if stats.count >= self._min_samples
            )
        )
