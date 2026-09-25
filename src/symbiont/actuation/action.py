"""Sensorimotor v2 action contracts.

High-level action selection is separated from low-level motor control. A
proposal is organism-owned intent; a MotorCommand is one controller correction
made under exactly one existing ActionCommitment and exactly one actuator
surface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


def _unit(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{field} must be within [0, 1]")
    return value


class ActionSource(StrEnum):
    EXPLORATION = "exploration"
    COMPETENCE = "competence"
    PROSPECTION = "prospection"
    PROTECTION = "protection"
    REGULATION = "regulation"


@dataclass(frozen=True, slots=True)
class ActionEvaluation:
    """Vector-valued evaluation; deliberately not a scalar reward."""

    epistemic_relevance: float = 0.0
    homeostatic_relevance: float = 0.0
    protective_relevance: float = 0.0
    effect_confidence: float = 0.0
    controllability: float | None = None
    uncertainty: float = 1.0
    estimated_cost: float | None = None
    estimated_risk: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "epistemic_relevance",
            "homeostatic_relevance",
            "protective_relevance",
            "effect_confidence",
            "uncertainty",
        ):
            object.__setattr__(self, name, _unit(getattr(self, name), name))
        for name in ("controllability", "estimated_cost", "estimated_risk"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _unit(value, name))


@dataclass(frozen=True, slots=True)
class ActionJustification:
    originating_need_id: str | None = None
    effect_target_id: str | None = None
    competence_id: str | None = None
    prediction_id: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionProposal:
    proposal_id: str
    source: ActionSource
    effect_target_id: str | None
    competence_id: str | None
    justification: ActionJustification
    evaluation: ActionEvaluation

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id must not be empty")
        if (
            self.justification.effect_target_id is not None
            and self.effect_target_id != self.justification.effect_target_id
        ):
            raise ValueError("proposal/justification effect target mismatch")
        if (
            self.justification.competence_id is not None
            and self.competence_id != self.justification.competence_id
        ):
            raise ValueError("proposal/justification competence mismatch")


@dataclass(frozen=True, slots=True)
class MotorCommand:
    """One low-level correction under an already selected commitment."""

    command_id: str
    commitment_id: str
    controller_id: str
    competence_id: str | None
    surface_fingerprint: str
    channels: tuple[tuple[str, float], ...]
    issued_at_tick: int
    embodiment_id: str | None = None

    def __post_init__(self) -> None:
        if not self.command_id:
            raise ValueError("command_id must not be empty")
        if not self.commitment_id or not self.controller_id:
            raise ValueError("motor command provenance must not be empty")
        if not self.surface_fingerprint:
            raise ValueError("motor command requires a surface fingerprint")
        if self.issued_at_tick < 0:
            raise ValueError("issued_at_tick must be non-negative")
        seen: set[str] = set()
        normalized: list[tuple[str, float]] = []
        for actuator_id, activation in self.channels:
            if not actuator_id or actuator_id in seen:
                raise ValueError("motor command channels must be unique and non-empty")
            seen.add(actuator_id)
            normalized.append((actuator_id, _unit(activation, "activation")))
        object.__setattr__(self, "channels", tuple(normalized))

    @classmethod
    def from_mapping(
        cls,
        *,
        command_id: str,
        commitment_id: str,
        controller_id: str,
        competence_id: str | None,
        surface_fingerprint: str,
        channels: Mapping[str, float],
        issued_at_tick: int,
        embodiment_id: str | None = None,
    ) -> "MotorCommand":
        return cls(
            command_id=command_id,
            commitment_id=commitment_id,
            controller_id=controller_id,
            competence_id=competence_id,
            surface_fingerprint=surface_fingerprint,
            channels=tuple(sorted((str(k), float(v)) for k, v in channels.items())),
            issued_at_tick=issued_at_tick,
            embodiment_id=embodiment_id,
        )
