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
