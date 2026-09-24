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
    competence_id: str | None
    state_before_ref: str
    motor_command_ref: str
    actuation_ref: str
    prediction_ref: str | None
    state_after_ref: str
    observed_effect_id: str | None = None
    prediction_error: PredictionError | None = None
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
        if self.observed_effect_id is not None and not self.observed_effect_id.startswith("effect."):
            raise ValueError("observed effect must be organism-owned")


@dataclass(frozen=True, slots=True)
class CausalEvidence:
    evidence_id: str
    transition_id: str
    action_ref: str
    competence_id: str | None
    effect_id: str | None
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

    SCHEMA_VERSION = 2

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
            competence_id=transition.competence_id,
            effect_id=transition.observed_effect_id,
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

    def effect_opportunities(
        self,
        effect_id: str,
        *,
        competence_id: str,
        context_ref: str | None = None,
    ) -> tuple[int, int, int, int]:
        """Return action opportunities/successes and alternative opportunities/successes."""
        action_n = action_success = other_n = other_success = 0
        for item in self._evidence:
            if context_ref is not None and item.context_ref != context_ref:
                continue
            hit = item.effect_id == effect_id
            if item.competence_id == competence_id:
                action_n += 1
                action_success += int(hit)
            else:
                other_n += 1
                other_success += int(hit)
        return action_n, action_success, other_n, other_success

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self._capacity,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "transition_id": item.transition_id,
                    "action_ref": item.action_ref,
                    "competence_id": item.competence_id,
                    "effect_id": item.effect_id,
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
        version = payload.get("schema_version")
        if version not in (1, cls.SCHEMA_VERSION):
            raise ValueError("unsupported causal-evidence checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 4096)))
        raw = payload.get("evidence", [])
        if not isinstance(raw, list):
            raise ValueError("invalid causal evidence")
        for item in raw[-obj._capacity:]:
            if not isinstance(item, dict):
                raise ValueError("invalid causal evidence item")
            normalized = dict(item)
            if version == 1:
                normalized.setdefault("competence_id", None)
                normalized.setdefault("effect_id", None)
            obj._evidence.append(CausalEvidence(**normalized))
        return obj
