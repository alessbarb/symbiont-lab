"""WorldEvent and the append-only journal (docs/design §6).

causal_parent_ids is reserved for mechanical causality the kernel
guarantees by construction; everything that depends on accumulated state
or multiple concurrent antecedents goes in contributing_event_ids instead.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

EVENT_KINDS = frozenset(
    {
        "WORLD_FIELD_CHANGED",
        "RESOURCE_RENEWED",
        "ORGANISM_MOVED",
        "MOVE",
        "ACTUATION_RESOLVED",
        "SUBSTRATE_IMPULSE",
        "ECOLOGY_CHANGED",
        "RESOURCE_ACQUIRED",
        "ORGANISM_EMITTED",
        "ORGANISM_CONTACT",
        "HAZARD_EXPOSURE",
        "PHYSIOLOGICAL_DAMAGE",
        "PHYSIOLOGY_BALANCE",
        "REPAIR",
        "BIRTH",
        "DEATH",
        "GENOME_MUTATION",
        "CULTURAL_TRANSMISSION",
    }
)


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
        self._first_index_by_event_id: dict[str, int] = {}
        self._events_by_tick: dict[int, list[WorldEvent]] = {}
        self._prefix_digests: list[str] = []

    @staticmethod
    def _snapshot_event(event: WorldEvent) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "world_id": event.world_id,
            "tick": event.tick,
            "kind": event.kind,
            "actor": event.actor,
            "position": event.position,
            "payload": dict(event.payload),
            "causal_parent_ids": list(event.causal_parent_ids),
            "contributing_event_ids": list(event.contributing_event_ids),
        }

    def append(self, event: WorldEvent) -> None:
        index = len(self._events)
        self._events.append(event)
        self._first_index_by_event_id.setdefault(event.event_id, index)
        self._events_by_tick.setdefault(event.tick, []).append(event)
        previous = self._prefix_digests[-1] if self._prefix_digests else ""
        encoded = json.dumps(
            self._snapshot_event(event),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._prefix_digests.append(
            hashlib.sha256(previous.encode("ascii") + b"\0" + encoded).hexdigest()
        )

    def stage(self, event: WorldEvent) -> None:
        self._staged.append(event)

    def commit_staged(self) -> tuple[WorldEvent, ...]:
        committed = tuple(self._staged)
        for event in committed:
            self.append(event)
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

    def events_for_tick(self, tick: int) -> tuple[WorldEvent, ...]:
        """Committed events for one World tick without replaying history."""
        return tuple(self._events_by_tick.get(int(tick), ()))

    def tail(self, limit: int) -> tuple[WorldEvent, ...]:
        """Return at most the latest committed events."""
        if limit < 0:
            raise ValueError("tail limit must be non-negative")
        if limit == 0:
            return ()
        return tuple(self._events[-limit:])

    def event_at(self, index: int) -> WorldEvent:
        """Return one committed event by append index."""
        return self._events[index]

    def prefix_digest(self, count: int | None = None) -> str:
        """Digest of a committed prefix, maintained incrementally on append."""
        resolved = len(self._events) if count is None else int(count)
        if resolved < 0 or resolved > len(self._events):
            raise ValueError("journal prefix count out of bounds")
        return "" if resolved == 0 else self._prefix_digests[resolved - 1]

    def snapshot_range(
        self,
        start: int = 0,
        stop: int | None = None,
    ) -> list[dict[str, Any]]:
        """Serialize only a bounded append range, not the complete history."""
        return [self._snapshot_event(event) for event in self._events[start:stop]]

    def page_after(
        self,
        after: str | None = None,
        *,
        limit: int = 256,
    ) -> tuple[tuple[WorldEvent, ...], str | None, bool]:
        """Return a page through append indexes, never a full-history replay."""
        if limit < 1:
            raise ValueError("event page limit must be positive")
        start = 0
        if after is not None:
            try:
                start = self._first_index_by_event_id[after] + 1
            except KeyError as exc:
                raise ValueError("unknown after event_id") from exc
        page = tuple(self._events[start : start + limit])
        next_after = page[-1].event_id if page else after
        return page, next_after, start + len(page) < len(self._events)

    def snapshot(self) -> list[dict[str, Any]]:
        return self.snapshot_range()

    @classmethod
    def from_snapshot(cls, events_data: list[dict[str, Any]]) -> "EventJournal":
        journal = cls()
        for d in events_data:
            journal.append(
                WorldEvent(
                    event_id=d["event_id"],
                    world_id=d["world_id"],
                    tick=d["tick"],
                    kind=d["kind"],
                    actor=d.get("actor"),
                    position=d.get("position"),
                    payload=d.get("payload", {}),
                    causal_parent_ids=tuple(d.get("causal_parent_ids", ())),
                    contributing_event_ids=tuple(d.get("contributing_event_ids", ())),
                )
            )
        return journal
