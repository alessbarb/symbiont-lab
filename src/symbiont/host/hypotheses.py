"""Evidence-gated lifecycle for relationships between opaque senses."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum

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
        if correlation is None:
            return
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
        key = tuple(sorted(source_ids))
        item = self._items.setdefault(key, SignalHypothesis(key, tick))
        item.update(correlation=correlation, samples=samples, min_samples=min_samples, tick=tick)

    @property
    def items(self) -> tuple[SignalHypothesis, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.id))
