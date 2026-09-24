"""Pure arbitration between constitutional urgency and ordinary agency."""
from __future__ import annotations

from dataclasses import dataclass

from .reactive_memory import ReactiveMemory
from .types import ReactiveState


@dataclass(frozen=True, slots=True)
class ArbitrationDecision:
    primitive_id: str | None
    reason: str


class ActionArbitrator:
    """Grant a learned fast response only under acute endogenous pressure."""

    def __init__(self, *, withdrawal_threshold: float = 0.55) -> None:
        if not 0.0 < float(withdrawal_threshold) <= 1.0:
            raise ValueError("withdrawal_threshold must be within (0, 1]")
        self._threshold = float(withdrawal_threshold)

    def choose_reactive(
        self,
        *,
        state: ReactiveState,
        memory: ReactiveMemory,
        candidate_ids: tuple[str, ...],
    ) -> ArbitrationDecision:
        if state.withdrawal < self._threshold:
            return ArbitrationDecision(None, "ordinary")
        primitive_id = memory.best(
            signature=state.signature,
            candidates=candidate_ids,
        )
        if primitive_id is None:
            return ArbitrationDecision(None, "acute_no_learned_response")
        return ArbitrationDecision(primitive_id, "reactive_learned_relief")
