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
    "HAZARD_EXPOSURE",
    "PHYSIOLOGICAL_DAMAGE",
    "REPAIR",
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
    """Append-only confirmed events. Staged events only commit on transaction success."""

    def __init__(self) -> None:
        self._events: list[WorldEvent] = []
        self._staged: list[WorldEvent] = []

    def append(self, event: WorldEvent) -> None:
        self._events.append(event)

    def stage(self, event: WorldEvent) -> None:
        self._staged.append(event)

    def commit_staged(self) -> tuple[WorldEvent, ...]:
        committed = tuple(self._staged)
        self._events.extend(self._staged)
        self._staged.clear()
        return committed

    def abort_staged(self) -> None:
        self._staged.clear()

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self):
        return iter(self._events)

    def replay(self) -> tuple[WorldEvent, ...]:
        return tuple(self._events)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "event_id": e.event_id,
                "world_id": e.world_id,
                "tick": e.tick,
                "kind": e.kind,
                "actor": e.actor,
                "position": e.position,
                "payload": dict(e.payload),
                "causal_parent_ids": list(e.causal_parent_ids),
                "contributing_event_ids": list(e.contributing_event_ids),
            }
            for e in self._events
        ]

    @classmethod
    def from_snapshot(cls, events_data: list[dict[str, Any]]) -> "EventJournal":
        journal = cls()
        for d in events_data:
            journal.append(WorldEvent(
                event_id=d["event_id"],
                world_id=d["world_id"],
                tick=d["tick"],
                kind=d["kind"],
                actor=d.get("actor"),
                position=d.get("position"),
                payload=d.get("payload", {}),
                causal_parent_ids=tuple(d.get("causal_parent_ids", ())),
                contributing_event_ids=tuple(d.get("contributing_event_ids", ())),
            ))
        return journal

