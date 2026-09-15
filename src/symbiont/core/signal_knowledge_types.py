from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .signal_identity import claim_id


@dataclass(frozen=True, slots=True)
class SignalObservation:
    signal_id: str
    available: bool
    selected: bool
    value: float | None = None
    quality: str = "unavailable"

    def __post_init__(self) -> None:
        if not isinstance(self.signal_id, str) or not self.signal_id.startswith("signal.") or len(self.signal_id) != 71:
            raise ValueError("signal_id must be opaque")
        if not isinstance(self.available, bool) or not isinstance(self.selected, bool):
            raise ValueError("availability flags must be bool")
        if self.value is not None and (isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value))):
            raise ValueError("value must be finite numeric or None")
        if self.quality not in {"nominal", "degraded", "stale", "unavailable"}:
            raise ValueError("unknown quality")

    @property
    def valid(self) -> bool:
        return self.available and self.selected and self.quality == "nominal" and self.value is not None


@dataclass(frozen=True, slots=True)
class SignalObservationBatch:
    tick: int
    observations: tuple[SignalObservation, ...]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a non-negative integer")
        ids = [o.signal_id for o in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate signal observations")


__all__ = ["SignalObservation", "SignalObservationBatch", "claim_id"]
