from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Any, Iterable

from .readings import ReadingQuality, SensorReading


@dataclass(slots=True)
class SenseState:
    """Learned, non-semantic description of one discovered host signal."""

    capability_id: str
    percept_name: str
    samples: int = 0
    available_samples: int = 0
    mean: float = 0.0
    m2: float = 0.0
    last_value: float | None = None
    delta_ewma: float = 0.0

    @property
    def variance(self) -> float:
        return self.m2 / (self.available_samples - 1) if self.available_samples > 1 else 0.0

    @property
    def availability(self) -> float:
        return self.available_samples / self.samples if self.samples else 0.0

    @property
    def utility(self) -> float:
        """Estimate usefulness from availability and information content only.

        No semantic label or hand-authored importance enters this score. A signal
        becomes useful by being observable and by changing enough to carry
        information relative to its own learned scale.
        """
        if self.available_samples < 2:
            return 0.0
        scale = abs(self.mean) + math.sqrt(max(0.0, self.variance)) + 1e-12
        variability = min(1.0, math.sqrt(max(0.0, self.variance)) / scale)
        motion = min(1.0, self.delta_ewma / scale)
        return self.availability * (0.65 * variability + 0.35 * motion)

    def observe(self, reading: SensorReading) -> None:
        self.samples += 1
        if reading.quality is ReadingQuality.UNAVAILABLE or reading.value is None:
            return
        value = float(reading.value)
        if not math.isfinite(value):
            return
        if self.last_value is not None:
            delta = abs(value - self.last_value)
            self.delta_ewma = delta if self.available_samples == 1 else (0.2 * delta + 0.8 * self.delta_ewma)
        self.last_value = value
        self.available_samples += 1
        delta = value - self.mean
        self.mean += delta / self.available_samples
        self.m2 += delta * (value - self.mean)

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "percept_name": self.percept_name,
            "samples": self.samples,
            "available_samples": self.available_samples,
            "mean": self.mean,
            "m2": self.m2,
            "last_value": self.last_value,
            "delta_ewma": self.delta_ewma,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SenseState":
        state = cls(
            capability_id=str(payload["capability_id"]),
            percept_name=str(payload["percept_name"]),
            samples=max(0, int(payload.get("samples", 0))),
            available_samples=max(0, int(payload.get("available_samples", 0))),
            mean=float(payload.get("mean", 0.0)),
            m2=max(0.0, float(payload.get("m2", 0.0))),
            last_value=(None if payload.get("last_value") is None else float(payload["last_value"])),
            delta_ewma=max(0.0, float(payload.get("delta_ewma", 0.0))),
        )
        if state.available_samples > state.samples:
            raise ValueError("available_samples cannot exceed samples")
        return state


class AdaptiveSenseModel:
    """Lets Symbiont develop a sensory repertoire from unknown safe signals.

    Providers discover possible read-only surfaces. This model is deliberately
    ignorant of what those surfaces mean. It gives each one an opaque percept
    identity, learns its statistics and decides which signals deserve routine
    attention from observed usefulness rather than a hard-coded sensor list.
    """

    def __init__(self, *, min_samples: int = 4, active_limit: int = 24) -> None:
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if active_limit < 1:
            raise ValueError("active_limit must be at least 1")
        self._min_samples = min_samples
        self._active_limit = active_limit
        self._states: dict[str, SenseState] = {}

    @staticmethod
    def _percept_name(capability_id: str) -> str:
        digest = sha256(f"symbiont-sense:{capability_id}".encode("utf-8")).hexdigest()[:12]
        return f"sense_{digest}"

    @property
    def states(self) -> tuple[SenseState, ...]:
        return tuple(sorted(self._states.values(), key=lambda item: item.percept_name))

    def observe(self, readings: Iterable[SensorReading]) -> None:
        for reading in readings:
            state = self._states.get(reading.capability_id)
            if state is None:
                state = SenseState(
                    capability_id=reading.capability_id,
                    percept_name=self._percept_name(reading.capability_id),
                )
                self._states[reading.capability_id] = state
            state.observe(reading)

    def percept_names(self) -> dict[str, str]:
        established = [state for state in self._states.values() if state.available_samples >= self._min_samples]
        ranked = sorted(established, key=lambda state: (-state.utility, state.percept_name))
        selected = ranked[: self._active_limit]
        return {state.capability_id: state.percept_name for state in selected}

    def export(self) -> dict[str, Any]:
        return {
            "min_samples": self._min_samples,
            "active_limit": self._active_limit,
            "states": [state.to_payload() for state in self.states],
        }

    @classmethod
    def restore(cls, payload: dict[str, Any] | None) -> "AdaptiveSenseModel":
        if not payload:
            return cls()
        model = cls(
            min_samples=int(payload.get("min_samples", 4)),
            active_limit=int(payload.get("active_limit", 24)),
        )
        for item in payload.get("states", []):
            state = SenseState.from_payload(item)
            model._states[state.capability_id] = state
        return model
