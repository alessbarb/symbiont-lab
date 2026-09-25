"""Temporal ownership of sensorimotor action."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommitmentStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    INCOMPATIBLE = "incompatible"
    INVALIDATED = "invalidated"


@dataclass(slots=True)
class ActionCommitment:
    commitment_id: str
    proposal_id: str
    effect_target_id: str | None
    competence_id: str | None
    started_tick: int
    controller_id: str
    surface_fingerprint: str
    embodiment_id: str | None = None
    interruptibility: float = 1.0
    minimum_duration: int = 0
    maximum_duration: int | None = None
    status: CommitmentStatus = CommitmentStatus.ACTIVE
    ended_tick: int | None = None
    end_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.commitment_id or not self.proposal_id or not self.controller_id:
            raise ValueError("commitment identifiers must not be empty")
        if not self.surface_fingerprint:
            raise ValueError("commitment requires a surface fingerprint")
        if self.started_tick < 0 or self.minimum_duration < 0:
            raise ValueError("commitment ticks must be non-negative")
        if self.maximum_duration is not None and self.maximum_duration < self.minimum_duration:
            raise ValueError("maximum_duration must be >= minimum_duration")
        if not 0.0 <= float(self.interruptibility) <= 1.0:
            raise ValueError("interruptibility must be within [0, 1]")

    @property
    def active(self) -> bool:
        return self.status is CommitmentStatus.ACTIVE

    def compatible_with(
        self,
        fingerprint: str | None,
        *,
        embodiment_id: str | None = None,
    ) -> bool:
        if fingerprint is None or fingerprint != self.surface_fingerprint:
            return False
        if (
            self.embodiment_id is not None
            and embodiment_id is not None
            and self.embodiment_id != embodiment_id
        ):
            return False
        return True

    def terminate(self, *, tick: int, status: CommitmentStatus, reason: str) -> None:
        if status is CommitmentStatus.ACTIVE:
            raise ValueError("terminate requires a terminal status")
        if not self.active:
            return
        if tick < self.started_tick:
            raise ValueError("end tick precedes commitment start")
        self.status = status
        self.ended_tick = tick
        self.end_reason = reason

    def checkpoint(self) -> dict[str, object]:
        return {
            "commitment_id": self.commitment_id,
            "proposal_id": self.proposal_id,
            "effect_target_id": self.effect_target_id,
            "competence_id": self.competence_id,
            "started_tick": self.started_tick,
            "controller_id": self.controller_id,
            "surface_fingerprint": self.surface_fingerprint,
            "embodiment_id": self.embodiment_id,
            "interruptibility": self.interruptibility,
            "minimum_duration": self.minimum_duration,
            "maximum_duration": self.maximum_duration,
            "status": self.status.value,
            "ended_tick": self.ended_tick,
            "end_reason": self.end_reason,
        }

    @classmethod
    def restore(
        cls,
        payload: dict[str, object],
        *,
        fallback_surface_fingerprint: str | None = None,
        fallback_embodiment_id: str | None = None,
    ) -> "ActionCommitment":
        fingerprint = payload.get("surface_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            fingerprint = fallback_surface_fingerprint
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError("legacy commitment requires an explicit current-surface migration")
        obj = cls(
            commitment_id=str(payload["commitment_id"]),
            proposal_id=str(payload["proposal_id"]),
            effect_target_id=payload.get("effect_target_id")
            if isinstance(payload.get("effect_target_id"), str)
            else None,
            competence_id=payload.get("competence_id")
            if isinstance(payload.get("competence_id"), str)
            else None,
            started_tick=int(payload["started_tick"]),
            controller_id=str(payload["controller_id"]),
            surface_fingerprint=fingerprint,
            embodiment_id=(
                payload.get("embodiment_id")
                if isinstance(payload.get("embodiment_id"), str)
                else fallback_embodiment_id
            ),
            interruptibility=float(payload.get("interruptibility", 1.0)),
            minimum_duration=int(payload.get("minimum_duration", 0)),
            maximum_duration=int(payload["maximum_duration"])
            if payload.get("maximum_duration") is not None
            else None,
            status=CommitmentStatus(str(payload.get("status", "active"))),
        )
        ended = payload.get("ended_tick")
        obj.ended_tick = int(ended) if ended is not None else None
        reason = payload.get("end_reason")
        obj.end_reason = str(reason) if reason is not None else None
        return obj
