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


_MATURITY_THRESHOLDS = (0, 1, 2, 4, 8, 16, 32, 64)  # support_epochs lower bound per class


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
