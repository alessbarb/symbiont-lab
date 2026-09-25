"""Typed orchestration context shared by organism domains."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickContext:
    symbiont_id: str
    symbiont_tick: int
    embodiment_id: str | None = None
    embodiment_tick: int | None = None
    body_id: str | None = None

    def __post_init__(self) -> None:
        if not self.symbiont_id:
            raise ValueError("symbiont_id must not be empty")
        if self.symbiont_tick < 0:
            raise ValueError("symbiont_tick must be non-negative")
        if self.embodiment_id is not None and not self.embodiment_id:
            raise ValueError("embodiment_id must be non-empty when provided")
        if self.body_id is not None and not self.body_id:
            raise ValueError("body_id must be non-empty when provided")
        if self.embodiment_tick is not None and self.embodiment_tick < 0:
            raise ValueError("embodiment_tick must be non-negative")
        if self.embodiment_id is None and (
            self.body_id is not None or self.embodiment_tick is not None
        ):
            raise ValueError("body_id/embodiment_tick require an embodiment_id")
