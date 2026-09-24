"""Canonical factual evidence for Sensorimotor v2."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PredictionError:
    magnitude: float
    directional_error: float | None = None
    timing_error: float | None = None
    uncertainty: float = 1.0
    novelty: float = 0.0

    def __post_init__(self) -> None:
        for name in ("magnitude", "uncertainty", "novelty"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class SensorimotorTransition:
    transition_id: str
    tick_start: int
    tick_end: int
    context_ref: str
    commitment_id: str
    controller_id: str
    state_before_ref: str
    motor_command_ref: str
    actuation_ref: str
    prediction_ref: str | None
    state_after_ref: str
    physiological_delta_ref: str | None = None

    def __post_init__(self) -> None:
        if self.tick_start < 0 or self.tick_end < self.tick_start:
            raise ValueError("invalid transition ticks")
        for value in (
            self.transition_id,
            self.context_ref,
            self.commitment_id,
            self.controller_id,
            self.state_before_ref,
            self.motor_command_ref,
            self.actuation_ref,
            self.state_after_ref,
        ):
            if not value:
                raise ValueError("transition references must not be empty")


@dataclass(frozen=True, slots=True)
class CausalEvidence:
    evidence_id: str
    transition_id: str
    action_ref: str
    context_ref: str
    prior_state_ref: str
    resulting_state_ref: str
    prediction_ref: str | None
    observation_tick: int

    def __post_init__(self) -> None:
        if self.observation_tick < 0:
            raise ValueError("observation_tick must be non-negative")


class CausalEvidenceLedger:
    """Single bounded factual source for all sensorimotor inference views."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 4096) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = int(capacity)
        self._evidence: list[CausalEvidence] = []

    def observe(self, transition: SensorimotorTransition) -> CausalEvidence:
        evidence = CausalEvidence(
            evidence_id=f"causal.{transition.transition_id}",
            transition_id=transition.transition_id,
            action_ref=transition.motor_command_ref,
            context_ref=transition.context_ref,
            prior_state_ref=transition.state_before_ref,
            resulting_state_ref=transition.state_after_ref,
            prediction_ref=transition.prediction_ref,
            observation_tick=transition.tick_end,
        )
        self._evidence.append(evidence)
        if len(self._evidence) > self._capacity:
            del self._evidence[: len(self._evidence) - self._capacity]
        return evidence

    @property
    def evidence(self) -> tuple[CausalEvidence, ...]:
        return tuple(self._evidence)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self._capacity,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "transition_id": item.transition_id,
                    "action_ref": item.action_ref,
                    "context_ref": item.context_ref,
                    "prior_state_ref": item.prior_state_ref,
                    "resulting_state_ref": item.resulting_state_ref,
                    "prediction_ref": item.prediction_ref,
                    "observation_tick": item.observation_tick,
                }
                for item in self._evidence
            ],
        }

    @classmethod
    def restore(cls, payload: dict[str, object]) -> "CausalEvidenceLedger":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported causal-evidence checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 4096)))
        raw = payload.get("evidence", [])
        if not isinstance(raw, list):
            raise ValueError("invalid causal evidence")
        for item in raw[-obj._capacity:]:
            if not isinstance(item, dict):
                raise ValueError("invalid causal evidence item")
            obj._evidence.append(CausalEvidence(**item))
        return obj
