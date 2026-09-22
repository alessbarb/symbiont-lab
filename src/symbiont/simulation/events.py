from __future__ import annotations

from dataclasses import dataclass

from symbiont.core.foundation.model import Observation


@dataclass(slots=True, frozen=True)
class EventContext:
    """Evaluator-only view of one synthetic event.

    The agent never receives this envelope. It exists so experiments can verify
    world parity and stratify outcomes without monkeypatching simulator internals.
    """

    step: int
    host_index: int
    truth_label: str
    is_threat: bool
    phase: str
    drift_state: str
    observation: Observation
