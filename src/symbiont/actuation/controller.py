"""Low-level controllers execute an existing commitment."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .action import MotorCommand
from .commitment import ActionCommitment
from .types import MotorIntent


@dataclass(slots=True)
class SequenceController:
    controller_id: str
    sequence: tuple[tuple[MotorIntent, ...], ...]
    step: int = 0

    def command(self, commitment: ActionCommitment, *, tick: int) -> MotorCommand:
        if not commitment.active:
            raise RuntimeError("cannot command an inactive commitment")
        if tick < commitment.started_tick:
            raise ValueError("controller tick precedes commitment")
        if not self.sequence:
            channels: tuple[tuple[str, float], ...] = ()
        else:
            frame = self.sequence[min(self.step, len(self.sequence) - 1)]
            channels = tuple(
                (intent.actuator_id, float(intent.activation))
                for intent in frame
            )
            self.step += 1
        material = "|".join(
            f"{actuator_id}:{activation:.12g}"
            for actuator_id, activation in channels
        )
        command_id = "command." + hashlib.sha256(
            f"{commitment.commitment_id}:{tick}:{material}".encode("utf-8")
        ).hexdigest()[:24]
        return MotorCommand(
            command_id=command_id,
            commitment_id=commitment.commitment_id,
            controller_id=self.controller_id,
            competence_id=commitment.competence_id,
            surface_fingerprint=commitment.surface_fingerprint,
            channels=channels,
            issued_at_tick=tick,
            embodiment_id=commitment.embodiment_id,
        )
