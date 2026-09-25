from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ResponsibilitySnapshot:
    losses: Mapping[str, float]
    responsibilities: Mapping[str, float]
    samples: Mapping[str, int]


class TemporalResponsibilityTracker:
    """Local explanatory responsibility across comparable temporal mechanisms.

    This tracker is intentionally scoped to one producer and one prediction
    target/context. It must never be used as a global structural scheduler.
    """

    def __init__(
        self,
        mechanism_ids: tuple[str, ...],
        *,
        smoothing: float = 0.125,
        temperature: float = 0.25,
    ) -> None:
        ids = tuple(dict.fromkeys(str(value) for value in mechanism_ids if str(value)))
        if not ids:
            raise ValueError("mechanism_ids must not be empty")
        if (
            isinstance(smoothing, bool)
            or not isinstance(smoothing, (int, float))
            or not 0.0 < float(smoothing) <= 1.0
        ):
            raise ValueError("smoothing must be within (0, 1]")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(float(temperature))
            or float(temperature) <= 0.0
        ):
            raise ValueError("temperature must be positive")

        self._ids = ids
        self._smoothing = float(smoothing)
        self._temperature = float(temperature)
        self._losses = {mechanism_id: 0.0 for mechanism_id in ids}
        self._samples = {mechanism_id: 0 for mechanism_id in ids}

    def observe(self, mechanism_id: str, *, loss: float) -> None:
        if mechanism_id not in self._losses:
            raise KeyError(mechanism_id)
        if (
            isinstance(loss, bool)
            or not isinstance(loss, (int, float))
            or not math.isfinite(float(loss))
            or float(loss) < 0.0
        ):
            raise ValueError("loss must be finite and non-negative")

        value = float(loss)
        samples = self._samples[mechanism_id]
        previous = self._losses[mechanism_id]
        self._losses[mechanism_id] = (
            value if samples == 0 else (1.0 - self._smoothing) * previous + self._smoothing * value
        )
        self._samples[mechanism_id] = samples + 1

    def responsibilities(self) -> dict[str, float]:
        observed = [mechanism_id for mechanism_id in self._ids if self._samples[mechanism_id] > 0]
        if not observed:
            share = 1.0 / len(self._ids)
            return {mechanism_id: share for mechanism_id in self._ids}

        # Lower local predictive loss yields greater responsibility. Subtracting
        # the minimum loss keeps exponentials numerically stable without
        # changing relative responsibility.
        minimum = min(self._losses[mechanism_id] for mechanism_id in observed)
        weights: dict[str, float] = {}
        for mechanism_id in self._ids:
            if self._samples[mechanism_id] == 0:
                weights[mechanism_id] = 0.0
                continue
            delta = self._losses[mechanism_id] - minimum
            weights[mechanism_id] = math.exp(-delta / self._temperature)

        total = sum(weights.values())
        if total <= 0.0:
            share = 1.0 / len(observed)
            return {
                mechanism_id: share if mechanism_id in observed else 0.0
                for mechanism_id in self._ids
            }
        return {mechanism_id: weights[mechanism_id] / total for mechanism_id in self._ids}

    def snapshot(self) -> ResponsibilitySnapshot:
        return ResponsibilitySnapshot(
            losses=dict(self._losses),
            responsibilities=self.responsibilities(),
            samples=dict(self._samples),
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "mechanism_ids": list(self._ids),
            "smoothing": self._smoothing,
            "temperature": self._temperature,
            "losses": dict(self._losses),
            "samples": dict(self._samples),
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "TemporalResponsibilityTracker":
        raw_ids = payload.get("mechanism_ids")
        if not isinstance(raw_ids, list):
            raise ValueError("mechanism_ids must be a list")
        tracker = cls(
            tuple(str(value) for value in raw_ids),
            smoothing=float(payload.get("smoothing", 0.125)),
            temperature=float(payload.get("temperature", 0.25)),
        )
        raw_losses = payload.get("losses", {})
        raw_samples = payload.get("samples", {})
        if not isinstance(raw_losses, Mapping) or not isinstance(raw_samples, Mapping):
            raise ValueError("losses and samples must be mappings")

        for mechanism_id in tracker._ids:
            samples = raw_samples.get(mechanism_id, 0)
            loss = raw_losses.get(mechanism_id, 0.0)
            if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
                raise ValueError("samples must be non-negative integers")
            if (
                isinstance(loss, bool)
                or not isinstance(loss, (int, float))
                or not math.isfinite(float(loss))
                or float(loss) < 0.0
            ):
                raise ValueError("losses must be finite and non-negative")
            tracker._samples[mechanism_id] = samples
            tracker._losses[mechanism_id] = float(loss)
        return tracker


__all__ = [
    "ResponsibilitySnapshot",
    "TemporalResponsibilityTracker",
]
