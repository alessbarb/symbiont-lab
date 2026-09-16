"""Evidence-gated lifecycle for relationships between opaque senses."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import math

class HypothesisStatus(StrEnum):
    CANDIDATE = "candidate"
    PROVISIONAL = "provisional"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    RETIRED = "retired"

@dataclass(slots=True)
class SignalHypothesis:
    source_ids: tuple[str, str]
    born_tick: int
    evidence_samples: int = 0
    validation_samples: int = 0
    observed_strength: float = 0.0
    sign_stability: float = 0.0
    status: HypothesisStatus = HypothesisStatus.CANDIDATE

    @property
    def id(self) -> str:
        return f"{self.source_ids[0]}::{self.source_ids[1]}"

    def update(self, *, correlation: float | None, samples: int, min_samples: int, tick: int) -> None:
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
            raise ValueError("samples must be a non-negative integer")
        if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 3:
            raise ValueError("min_samples must be an integer >= 3")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if correlation is None:
            return
        if isinstance(correlation, bool) or not math.isfinite(correlation) or not -1.0 <= correlation <= 1.0:
            raise ValueError("correlation must be finite and within [-1, 1]")
        self.evidence_samples = samples
        self.observed_strength = abs(correlation)
        if samples < min_samples:
            self.status = HypothesisStatus.CANDIDATE
            return
        self.validation_samples = max(0, samples - min_samples)
        self.sign_stability = 1.0 if correlation != 0 else 0.0
        if self.validation_samples < min_samples:
            self.status = HypothesisStatus.PROVISIONAL
        elif self.observed_strength >= 0.5:
            self.status = HypothesisStatus.SUPPORTED
        else:
            self.status = HypothesisStatus.CONTRADICTED

class HypothesisTracker:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], SignalHypothesis] = {}

    def observe(self, source_ids: tuple[str, str], *, correlation: float | None, samples: int, min_samples: int, tick: int) -> None:
        if not isinstance(source_ids, tuple) or len(source_ids) != 2:
            raise ValueError("source_ids must contain exactly two identifiers")
        if any(not isinstance(source_id, str) or not source_id or len(source_id) > 128 for source_id in source_ids):
            raise ValueError("source_ids must be non-empty bounded strings")
        if source_ids[0] == source_ids[1]:
            raise ValueError("source_ids must identify two distinct sources")
        key = tuple(sorted(source_ids))
        item = self._items.setdefault(key, SignalHypothesis(key, tick))
        item.update(correlation=correlation, samples=samples, min_samples=min_samples, tick=tick)

    @property
    def items(self) -> tuple[SignalHypothesis, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.id))
