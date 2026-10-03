"""Innate, body-agnostic reactivity.

Detects when ordinary behaviour should be interrupted or given defensive
priority. It never chooses actuators and contains no anatomy, Physics3D,
environment, resource, or task semantics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from .types import ReactiveState


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class InnateReactivity:
    """Convert opaque percept change plus physiology into urgency."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        surprise_threshold: float = 0.18,
        acute_velocity: float = 0.05,
        smoothing: float = 0.35,
    ) -> None:
        for name, value in (
            ("surprise_threshold", surprise_threshold),
            ("acute_velocity", acute_velocity),
            ("smoothing", smoothing),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0.0
            ):
                raise ValueError(f"{name} must be finite and positive")
        if float(smoothing) > 1.0:
            raise ValueError("smoothing must be <= 1")
        self._surprise_threshold = float(surprise_threshold)
        self._acute_velocity = float(acute_velocity)
        self._smoothing = float(smoothing)
        self._previous_deviation: float | None = None
        self._previous_percepts: dict[str, float] = {}
        self._smoothed_velocity = 0.0

    @staticmethod
    def _finite_percepts(percepts: Mapping[str, float]) -> dict[str, float]:
        result: dict[str, float] = {}
        for key, value in percepts.items():
            if (
                isinstance(key, str)
                and key
                and not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
            ):
                result[key] = float(value)
        return result

    def evaluate(
        self,
        *,
        percepts: Mapping[str, float],
        homeostatic_deviation: float,
    ) -> ReactiveState:
        deviation = _unit(homeostatic_deviation)
        current = self._finite_percepts(percepts)
        raw_velocity = (
            0.0 if self._previous_deviation is None else deviation - self._previous_deviation
        )
        self._smoothed_velocity = (
            self._smoothing * raw_velocity + (1.0 - self._smoothing) * self._smoothed_velocity
        )
        shared = set(current).intersection(self._previous_percepts)
        surprise = max(
            (min(1.0, abs(current[key] - self._previous_percepts[key])) for key in shared),
            default=0.0,
        )
        worsening = _unit(max(0.0, self._smoothed_velocity) / self._acute_velocity)
        criticality = _unit((deviation - 0.55) / 0.45)
        novelty = _unit(
            max(0.0, surprise - self._surprise_threshold)
            / max(1e-12, 1.0 - self._surprise_threshold)
        )
        withdrawal = _unit(max(worsening, worsening * (0.5 + 0.5 * deviation)))
        interrupt = _unit(max(novelty, withdrawal))
        conservation = _unit(max(criticality, deviation * worsening))
        stabilization = _unit(max(withdrawal * 0.75, criticality * 0.65))
        attention = _unit(max(interrupt, surprise))
        pressure_bin = min(3, int(withdrawal * 4.0))
        surprise_bin = min(3, int(surprise * 4.0))
        critical_bin = min(3, int(criticality * 4.0))
        signature = f"r{pressure_bin}:s{surprise_bin}:c{critical_bin}"
        self._previous_deviation = deviation
        self._previous_percepts = current
        return ReactiveState(
            interrupt=interrupt,
            withdrawal=withdrawal,
            stabilization=stabilization,
            conservation=conservation,
            attention=attention,
            deviation=deviation,
            deviation_velocity=self._smoothed_velocity,
            surprise=surprise,
            signature=signature,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "surprise_threshold": self._surprise_threshold,
            "acute_velocity": self._acute_velocity,
            "smoothing": self._smoothing,
            "previous_deviation": self._previous_deviation,
            "previous_percepts": dict(sorted(self._previous_percepts.items())),
            "smoothed_velocity": self._smoothed_velocity,
        }

    @classmethod
    def restore(cls, payload: object) -> "InnateReactivity":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid innate reactivity checkpoint")
        obj = cls(
            surprise_threshold=float(payload["surprise_threshold"]),
            acute_velocity=float(payload["acute_velocity"]),
            smoothing=float(payload["smoothing"]),
        )
        previous = payload.get("previous_deviation")
        if previous is not None:
            if not isinstance(previous, (int, float)) or isinstance(previous, bool):
                raise ValueError("invalid previous deviation")
            obj._previous_deviation = _unit(float(previous))
        raw = payload.get("previous_percepts", {})
        if not isinstance(raw, dict):
            raise ValueError("invalid previous percepts")
        obj._previous_percepts = obj._finite_percepts(raw)
        smoothed = float(payload.get("smoothed_velocity", 0.0))
        if not math.isfinite(smoothed):
            raise ValueError("invalid smoothed velocity")
        obj._smoothed_velocity = smoothed
        return obj
