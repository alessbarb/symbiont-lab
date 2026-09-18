"""WorldEvent and the append-only journal (docs/design §6).

causal_parent_ids is reserved for mechanical causality the kernel
guarantees by construction; everything that depends on accumulated state
or multiple concurrent antecedents goes in contributing_event_ids instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

EVENT_KINDS = frozenset({
    "WORLD_FIELD_CHANGED",
    "RESOURCE_RENEWED",
    "ORGANISM_MOVED",
    "RESOURCE_ACQUIRED",
    "ORGANISM_EMITTED",
    "ORGANISM_CONTACT",
    "BIRTH",
    "DEATH",
    "GENOME_MUTATION",
    "CULTURAL_TRANSMISSION",
})


@dataclass(frozen=True, slots=True)
class WorldEvent:
    event_id: str
    world_id: str
    tick: int
    kind: str
    actor: str | None
    position: str | None
    payload: Mapping[str, Any] = field(default_factory=dict)
    causal_parent_ids: tuple[str, ...] = ()
    contributing_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"unknown WorldEvent kind: {self.kind!r}")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "causal_parent_ids", tuple(self.causal_parent_ids))
        object.__setattr__(self, "contributing_event_ids", tuple(self.contributing_event_ids))


class EventJournal:
    """Append-only. No update or delete method exists on purpose."""

    def __init__(self) -> None:
        self._events: list[WorldEvent] = []

    def append(self, event: WorldEvent) -> None:
        self._events.append(event)

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self):
        return iter(self._events)

    def replay(self) -> tuple[WorldEvent, ...]:
        return tuple(self._events)
