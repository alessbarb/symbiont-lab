"""Deferred-damage resource effect (docs/design/symbiont-world-v2.md §6):
the "immediate benefit, delayed damage" resource v1 §7 required but never
modeled. Lives entirely in symbiont_lab -- no new API in symbiont_world or
symbiont; fires through the existing apply_environmental_damage.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_QUEUE_SIZE = 32


@dataclass(frozen=True, slots=True)
class DeferredEffect:
    organism_id: str
    due_tick: int
    amount: float

    def __post_init__(self) -> None:
        if not 0.0 < self.amount <= 0.25:
            raise ValueError("amount must be within (0, 0.25], matching apply_environmental_damage")
        if self.due_tick < 0:
            raise ValueError("due_tick must be non-negative")


class DeferredEffectQueue:
    """Bounded: an organism cannot accumulate unlimited pending damage."""

    def __init__(self, max_size: int = MAX_QUEUE_SIZE) -> None:
        self._max_size = max_size
        self._pending: list[DeferredEffect] = []

    def __len__(self) -> int:
        return len(self._pending)

    def schedule(self, effect: DeferredEffect) -> bool:
        if len(self._pending) >= self._max_size:
            return False
        self._pending.append(effect)
        return True

    def pop_due(self, organism_id: str, current_tick: int) -> tuple[DeferredEffect, ...]:
        due = tuple(
            effect
            for effect in self._pending
            if effect.organism_id == organism_id and effect.due_tick <= current_tick
        )
        if due:
            self._pending = [effect for effect in self._pending if effect not in due]
        return due

    def snapshot(self) -> list[dict[str, object]]:
        return [
            {"organism_id": e.organism_id, "due_tick": e.due_tick, "amount": e.amount}
            for e in self._pending
        ]

    def restore(self, snap: list[dict[str, object]]) -> None:
        self._pending = [
            DeferredEffect(organism_id=str(d["organism_id"]), due_tick=int(d["due_tick"]), amount=float(d["amount"]))
            for d in snap
        ]

    @classmethod
    def from_snapshot(cls, snap: list[dict[str, object]], max_size: int = MAX_QUEUE_SIZE) -> "DeferredEffectQueue":
        q = cls(max_size=max_size)
        q.restore(snap)
        return q

