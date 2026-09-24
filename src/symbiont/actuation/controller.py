"""Low-level controllers execute an existing commitment."""
from __future__ import annotations

from dataclasses import dataclass

from .action import MotorCommand
from .commitment import ActionCommitment
from .types import MotorIntent


@dataclass(slots=True)
class SequenceController:
    controller_id: str
    sequence: tuple[tuple[MotorIntent, ...], ...]
    step: int = 0

    def command(self, commitment: ActionCommitment) -> MotorCommand:
        if not commitment.active:
            raise RuntimeError("cannot command an inactive commitment")
        if not self.sequence:
            channels: tuple[tuple[str, float], ...] = ()
        else:
            frame = self.sequence[min(self.step, len(self.sequence) - 1)]
            channels = tuple((intent.actuator_id, float(intent.activation)) for intent in frame)
            self.step += 1
        return MotorCommand(
            commitment_id=commitment.commitment_id,
            controller_id=self.controller_id,
            competence_id=commitment.competence_id,
            channels=channels,
        )
