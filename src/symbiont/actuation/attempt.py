"""Concrete physical interventions (Agency Acquisition v1 §9-§10).

An ActionAttempt records only that one issued MotorCommand crossed the body
boundary under one commitment.  It is the causal atom of execution: it does
not name a skill, does not require a competence and never asserts which
consequence it produced.  Consequences are attached later by the causal
ledger once the following bodily state is actually observed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace


def attempt_id_for_command(command_id: str) -> str:
    """One issued MotorCommand -> exactly one deterministic attempt identity."""
    if not command_id:
        raise ValueError("attempt requires an issued motor command")
    digest = hashlib.sha256(f"action-attempt:{command_id}".encode("utf-8")).hexdigest()[:24]
    return f"attempt.{digest}"


@dataclass(frozen=True, slots=True)
class ActionAttempt:
    attempt_id: str

    commitment_id: str
    controller_id: str

    competence_id: str | None

    intervention_signature_id: str

    context_ref: str
    embodiment_id: str | None
    surface_fingerprint: str

    motor_command_ref: str
    actuation_ref: str

    started_tick: int
    completed_tick: int | None = None

    def __post_init__(self) -> None:
        if not self.attempt_id.startswith("attempt."):
            raise ValueError("attempt_id must be an opaque attempt reference")
        for value in (
            self.commitment_id,
            self.controller_id,
            self.intervention_signature_id,
            self.context_ref,
            self.surface_fingerprint,
            self.motor_command_ref,
            self.actuation_ref,
        ):
            if not value:
                raise ValueError("attempt references must not be empty")
        if self.competence_id is not None and not self.competence_id:
            raise ValueError("competence_id must be None or non-empty")
        if self.started_tick < 0:
            raise ValueError("started_tick must be non-negative")
        if self.completed_tick is not None and self.completed_tick <= self.started_tick:
            # A command is never credited with a same-tick consequence.
            raise ValueError("an attempt closes only on a later observation")

    @property
    def open(self) -> bool:
        return self.completed_tick is None

    def close(self, *, tick: int) -> "ActionAttempt":
        if not self.open:
            raise ValueError("attempt already closed")
        return replace(self, completed_tick=int(tick))


__all__ = ["ActionAttempt", "attempt_id_for_command"]
