"""Acquisition protection versus World consequence completeness (ADR-0008 §3-4).

A policy only decides whether the Lab ends the run. It never repairs the body,
chooses actions, rewards, or edits evidence; it reads state that the causal
tick computes regardless of observation.
"""

from __future__ import annotations

from dataclasses import dataclass

from lab.experience.definition import GUARD_PREFIX, RunKind, TerminationReason

# Physiology enters these under SEVERE resource pressure, one step before the
# irreversible UNRECOVERABLE -> DEAD transition.
PROTECTED_VITAL_STATES = frozenset({"agonizing", "dormant"})


@dataclass(frozen=True, slots=True)
class AcquisitionSafetyPolicy:
    protected_vital_states: frozenset[str] = PROTECTED_VITAL_STATES

    def assess(self, *, alive: bool, vital_state: str) -> TerminationReason | None:
        if not alive:
            return TerminationReason.BODY_NON_VIABLE  # protection breach, recorded as such
        if vital_state in self.protected_vital_states:
            return TerminationReason.PROTECTED_RECOVERY
        return None

    def refuses_start(self, vital_state: str | None) -> bool:
        return vital_state == "dead" or vital_state in self.protected_vital_states


@dataclass(frozen=True, slots=True)
class WorldConsequencePolicy:
    """No rescue: the body lives or dies by the simulated consequences."""

    def assess(self, *, alive: bool, vital_state: str) -> TerminationReason | None:
        return None if alive else TerminationReason.BODY_NON_VIABLE

    def refuses_start(self, vital_state: str | None) -> bool:
        return vital_state == "dead"


def consequence_policy(kind: RunKind) -> AcquisitionSafetyPolicy | WorldConsequencePolicy:
    return AcquisitionSafetyPolicy() if kind.is_acquisition else WorldConsequencePolicy()


class RunGuard:
    """Engine-facing callable: ``guard(alive, vital_state) -> exit cause | None``."""

    __slots__ = ("policy", "triggered")

    def __init__(self, kind: RunKind) -> None:
        self.policy = consequence_policy(kind)
        self.triggered: TerminationReason | None = None

    def __call__(self, alive: bool, vital_state: str) -> str | None:
        reason = self.policy.assess(alive=alive, vital_state=vital_state)
        if reason is None:
            return None
        self.triggered = reason
        return GUARD_PREFIX + reason.value


__all__ = [
    "PROTECTED_VITAL_STATES",
    "AcquisitionSafetyPolicy",
    "RunGuard",
    "WorldConsequencePolicy",
    "consequence_policy",
]
