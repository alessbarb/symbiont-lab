"""Biological memory consolidation kernel (design: docs/design/biological-memory-consolidation.md).

Changes the persistence model from "serialize learned state" to "persist
consolidated memory": labile working state (RAM only) feeds a bounded
consolidation buffer, which commits into durable, coarse, checkpointable
memory only when independently supported or exceptionally salient. No raw
observation, exact tick, or host/provider identity is ever durable here.

Named ``consolidation.py`` rather than ``memory.py`` (the design's own
naming) because ``src/symbiont/core/memory.py`` already exists as the
legacy synthetic-ecology agent's episodic memory (imported by
``core/agent.py``, unrelated to the resident organism this module serves).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from ..cognition.limits import KernelLimits
from ..host.drift import DriftKind


class MemoryError(Exception):
    """Raised for any invalid memory-consolidation input or state."""


class MemoryKind(StrEnum):
    """Closed set of memory kinds -- each has its own consolidation rule
    (design §5). Never extended by a genome or by learned behavior."""

    STATISTICAL = "statistical"
    SALIENT_EVENT = "salient_event"
    STRUCTURAL = "structural"


_SIGNAL_FIELDS = ("novelty", "surprise", "attention", "reliability", "coherence")

# Kernel-owned, not organism-learnable in this release (design §7, §19).
_NOVELTY_WEIGHT = 0.20
_SURPRISE_WEIGHT = 0.30
_ATTENTION_WEIGHT = 0.20
_RELIABILITY_WEIGHT = 0.20
_COHERENCE_WEIGHT = 0.10


@dataclass(slots=True, frozen=True)
class ConsolidationSignal:
    """Every field is derived only from signals the organism already
    produces (drift kind, prediction error, attention selection, self-model
    health/availability, epoch-spaced support) -- never an external label
    (design §6)."""

    novelty: float
    surprise: float
    attention: float
    reliability: float
    coherence: float

    def __post_init__(self) -> None:
        for name in _SIGNAL_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise MemoryError(f"{name} must be a number")
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise MemoryError(f"{name} must be finite and within [0, 1]")

    def score(self) -> float:
        return (
            _NOVELTY_WEIGHT * self.novelty
            + _SURPRISE_WEIGHT * self.surprise
            + _ATTENTION_WEIGHT * self.attention
            + _RELIABILITY_WEIGHT * self.reliability
            + _COHERENCE_WEIGHT * self.coherence
        )


_NOVELTY_BY_DRIFT_KIND: dict[DriftKind, float] = {
    DriftKind.NONE: 0.00,
    DriftKind.GRADUAL: 0.35,
    DriftKind.CREEP: 0.50,
    DriftKind.ISOLATED: 0.70,
    DriftKind.REGIME_SHIFT: 0.90,
}


def novelty_from_drift_kind(kind: DriftKind | None) -> float:
    """Kernel mapping (design §6.1), not learned from any host label."""
    if kind is None:
        return 0.0
    return _NOVELTY_BY_DRIFT_KIND.get(kind, 0.0)


_SURPRISE_SATURATION_LOSS = 1.0  # loss at/above this saturates surprise to 1.0


def surprise_from_loss(loss: float | None) -> float:
    """No predictor means surprise contributes zero rather than being
    fabricated (design §6.2). Exact loss is never itself persisted --
    only this bounded transform ever reaches a ConsolidationSignal."""
    if loss is None or not isinstance(loss, (int, float)) or isinstance(loss, bool):
        return 0.0
    if not math.isfinite(loss) or loss < 0:
        return 0.0
    return max(0.0, min(1.0, loss / _SURPRISE_SATURATION_LOSS))


from .epistemic import DEFAULT_EPISTEMIC_CONVENTIONS

_MATURITY_THRESHOLDS = DEFAULT_EPISTEMIC_CONVENTIONS.maturity_thresholds  # support_epochs lower bound per class


def maturity_class_from_support_epochs(support_epochs: int) -> int:
    """Coarse, monotone class (design §10.1) -- no exact support_epochs
    count can be reconstructed from it. Eight classes: 0 trace .. 7
    saturated."""
    if support_epochs < 0:
        support_epochs = 0
    matured_class = 0
    for index, threshold in enumerate(_MATURITY_THRESHOLDS):
        if support_epochs >= threshold:
            matured_class = index
    return matured_class


@dataclass(slots=True)
class ConsolidationCandidate:
    """RAM-only working buffer entry (design §9.3). No raw observation is
    stored here -- only bounded epoch/strength bookkeeping."""

    key: str
    kind: MemoryKind
    support_epochs: int = 0
    last_support_epoch: int | None = None
    strength: float = 0.0
    latest_signal: ConsolidationSignal | None = None


_TRACE_CLASS_COUNT = 16


def quantize_unit(value: float, num_classes: int) -> int:
    """Maps a [0, 1] float to a class id in [0, num_classes - 1], clipping
    out-of-range input rather than raising -- this is a display/durable
    transform applied to already-validated signal values, not a boundary
    check in its own right."""
    clipped = max(0.0, min(1.0, value))
    return round(clipped * (num_classes - 1))


def _require_trace_class(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MemoryError(f"{field_name} must be an integer class id")
    if not 0 <= value < _TRACE_CLASS_COUNT:
        raise MemoryError(f"{field_name} must be within [0, {_TRACE_CLASS_COUNT - 1}]")


@dataclass(slots=True, frozen=True)
class SalientEventTrace:
    """Bounded durable record of one exceptional transition (design §10.5).
    No raw reading, exact z-score, exact prediction error, timestamp or
    provider identity -- only coarse categorical classes and a safe id."""

    pattern_id: str
    novelty_class: int
    surprise_class: int
    reliability_class: int
    context_class: int
    recurrence_class: int

    def __post_init__(self) -> None:
        if not isinstance(self.pattern_id, str) or not self.pattern_id:
            raise MemoryError("pattern_id must be a non-empty string")
        for field_name in ("novelty_class", "surprise_class", "reliability_class", "context_class", "recurrence_class"):
            _require_trace_class(getattr(self, field_name), field_name)


@dataclass(slots=True, frozen=True)
class ConsolidationOutcome:
    key: str
    kind: MemoryKind
    path: str  # "fast" or "slow"
    committed: bool
    support_epochs: int
    score: float


class MemoryConsolidator:
    """Orchestrates fast/slow consolidation (design §7, §9.5). Owns the
    RAM-only candidate buffer and the durable salient-trace/statistical
    projections. export_checkpoint() (added in a later task) exports only
    what has actually committed -- pending candidates never leave this
    class."""

    def __init__(self, *, kernel_limits: KernelLimits) -> None:
        self._kernel_limits = kernel_limits
        self._candidates: dict[str, ConsolidationCandidate] = {}
        self._committed_statistical: dict[str, int] = {}  # key -> maturity_class
        self._salient_traces: dict[str, SalientEventTrace] = {}
        self._salient_reinforced_epoch: dict[str, int] = {}

    @property
    def salient_events(self) -> tuple[SalientEventTrace, ...]:
        ordered_ids = sorted(self._salient_traces, key=lambda pattern_id: self._salient_reinforced_epoch[pattern_id])
        return tuple(self._salient_traces[pattern_id] for pattern_id in ordered_ids)

    def observe(
        self, key: str, kind: MemoryKind, signal: ConsolidationSignal, *, tick: int
    ) -> ConsolidationOutcome:
        epoch_id = tick // self._kernel_limits.consolidation_epoch_ticks
        score = signal.score()

        if (
            kind is MemoryKind.SALIENT_EVENT
            and score >= self._kernel_limits.fast_consolidation_threshold
            and signal.reliability >= self._kernel_limits.fast_min_reliability
        ):
            self._commit_salient_trace(key, signal, epoch_id=epoch_id)
            return ConsolidationOutcome(key=key, kind=kind, path="fast", committed=True, support_epochs=0, score=score)

        candidate = self._candidates.get(key)
        if candidate is None:
            if len(self._candidates) >= self._kernel_limits.max_consolidation_candidates:
                self._evict_one_candidate()
            candidate = ConsolidationCandidate(key=key, kind=kind)
            self._candidates[key] = candidate

        if candidate.last_support_epoch != epoch_id:
            candidate.support_epochs += 1
            candidate.last_support_epoch = epoch_id
        candidate.strength = score
        candidate.latest_signal = signal

        committed = candidate.support_epochs >= self._kernel_limits.slow_support_epochs
        if committed and kind is MemoryKind.STATISTICAL:
            self._committed_statistical[key] = maturity_class_from_support_epochs(candidate.support_epochs)

        return ConsolidationOutcome(
            key=key, kind=kind, path="slow", committed=committed,
            support_epochs=candidate.support_epochs, score=score,
        )

    def _commit_salient_trace(self, key: str, signal: ConsolidationSignal, *, epoch_id: int) -> None:
        existing = self._salient_traces.get(key)
        recurrence_class = min(15, (existing.recurrence_class + 1) if existing is not None else 0)
        trace = SalientEventTrace(
            pattern_id=key,
            novelty_class=quantize_unit(signal.novelty, _TRACE_CLASS_COUNT),
            surprise_class=quantize_unit(signal.surprise, _TRACE_CLASS_COUNT),
            reliability_class=quantize_unit(signal.reliability, _TRACE_CLASS_COUNT),
            context_class=existing.context_class if existing is not None else 0,
            recurrence_class=recurrence_class,
        )
        if key not in self._salient_traces and len(self._salient_traces) >= self._kernel_limits.max_salient_event_traces:
            self._evict_one_salient_trace()
        self._salient_traces[key] = trace
        self._salient_reinforced_epoch[key] = epoch_id

    def _evict_one_salient_trace(self) -> None:
        victim_id = min(self._salient_reinforced_epoch, key=lambda pattern_id: (self._salient_reinforced_epoch[pattern_id], pattern_id))
        del self._salient_traces[victim_id]
        del self._salient_reinforced_epoch[victim_id]

    def _evict_one_candidate(self) -> None:
        victim_key = min(
            self._candidates,
            key=lambda k: (self._candidates[k].last_support_epoch or -1, k),
        )
        del self._candidates[victim_key]

    def export_checkpoint(self) -> dict[str, object]:
        """Only committed/durable state -- pending candidates never appear
        here (design §4, §12.1). This is what makes P1/P2 true by
        construction: nothing here changes except at a real commit."""
        return {
            "statistical": dict(self._committed_statistical),
            "salient_events": [
                {
                    "pattern_id": trace.pattern_id,
                    "novelty_class": trace.novelty_class,
                    "surprise_class": trace.surprise_class,
                    "reliability_class": trace.reliability_class,
                    "context_class": trace.context_class,
                    "recurrence_class": trace.recurrence_class,
                }
                for trace in self.salient_events
            ],
        }

    @classmethod
    def restore_checkpoint(cls, payload: dict[str, object] | None, *, kernel_limits: KernelLimits) -> "MemoryConsolidator":
        consolidator = cls(kernel_limits=kernel_limits)
        if payload is None:
            return consolidator
        if not isinstance(payload, dict):
            raise MemoryError("memory checkpoint payload must be an object")
        statistical = payload.get("statistical", {})
        if not isinstance(statistical, dict):
            raise MemoryError("memory checkpoint 'statistical' must be an object")
        consolidator._committed_statistical = {str(key): int(value) for key, value in statistical.items()}
        salient_events = payload.get("salient_events", [])
        if not isinstance(salient_events, list):
            raise MemoryError("memory checkpoint 'salient_events' must be an array")
        for epoch, entry in enumerate(salient_events):
            trace = SalientEventTrace(
                pattern_id=str(entry["pattern_id"]),
                novelty_class=int(entry["novelty_class"]),
                surprise_class=int(entry["surprise_class"]),
                reliability_class=int(entry["reliability_class"]),
                context_class=int(entry["context_class"]),
                recurrence_class=int(entry["recurrence_class"]),
            )
            consolidator._salient_traces[trace.pattern_id] = trace
            consolidator._salient_reinforced_epoch[trace.pattern_id] = epoch
        return consolidator
