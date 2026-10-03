"""Causal Provenance v1 (docs/design/core/causal-provenance-v1.md).

One transversal contract for "why does this exist?": every state-changing
decision emits a ``CausalEvent`` naming what caused it and what it produced,
by stable, correlatable ``CausalRef``.  Timestamps say when; provenance says
why.

The organism keeps only a bounded ring of recent events and a **frontier**:
for every live reference, the refs of its immediate causes.  The frontier is
bounded by the number of live references, not by age, and is checkpointed, so
any live reference stays explainable after the ring wraps.  Durable history is
the lab's append-only journal, fed passively from the observation stream; it
never feeds back into the organism.

No raw values, no semantics: refs are structural kinds and opaque ids.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

RING_CAPACITY = 8192
MAX_CAUSES = 64


@dataclass(frozen=True, slots=True, order=True)
class CausalRef:
    kind: str
    id: str

    def __post_init__(self) -> None:
        if not self.kind or not self.id:
            raise ValueError("a causal ref needs a kind and an id")

    def payload(self) -> list[str]:
        return [self.kind, self.id]

    @classmethod
    def from_payload(cls, raw: Iterable[str]) -> "CausalRef":
        kind, ref_id = raw
        return cls(str(kind), str(ref_id))


def _scalar(value: Any) -> float | int | str | bool | None:
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, float):
        return round(value, 12)
    raise ValueError("provenance parameters must be scalars")


@dataclass(frozen=True, slots=True)
class CausalEvent:
    tick: int
    domain: str
    operation: str
    subject: CausalRef
    caused_by: tuple[CausalRef, ...]
    produced: tuple[CausalRef, ...] = ()
    rule: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def __post_init__(self) -> None:
        if len(self.caused_by) > MAX_CAUSES:
            raise ValueError("a causal event names a bounded set of causes")
        params = {str(k): _scalar(v) for k, v in sorted(dict(self.parameters).items())}
        object.__setattr__(self, "parameters", params)
        object.__setattr__(self, "caused_by", tuple(self.caused_by))
        object.__setattr__(self, "produced", tuple(self.produced))
        digest = hashlib.sha256(
            json.dumps(self._identity(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        object.__setattr__(self, "event_id", "event." + digest)

    def _identity(self) -> dict[str, Any]:
        return {
            "tick": int(self.tick),
            "domain": self.domain,
            "operation": self.operation,
            "subject": self.subject.payload(),
            "caused_by": [ref.payload() for ref in self.caused_by],
            "produced": [ref.payload() for ref in self.produced],
            "rule": self.rule,
            "parameters": dict(self.parameters),
        }

    def payload(self) -> dict[str, Any]:
        return {"event_id": self.event_id, **self._identity()}

    @classmethod
    def from_payload(cls, raw: Mapping[str, Any]) -> "CausalEvent":
        event = cls(
            tick=int(raw["tick"]),
            domain=str(raw["domain"]),
            operation=str(raw["operation"]),
            subject=CausalRef.from_payload(raw["subject"]),
            caused_by=tuple(CausalRef.from_payload(item) for item in raw["caused_by"]),
            produced=tuple(CausalRef.from_payload(item) for item in raw.get("produced", ())),
            rule=raw.get("rule"),
            parameters=dict(raw.get("parameters", {})),
        )
        if raw.get("event_id") not in (None, event.event_id):
            raise ValueError("causal event id does not match its content")
        return event


class ProvenanceLog:
    """Bounded ring of recent events plus the frontier of live references."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = RING_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._ring: deque[CausalEvent] = deque(maxlen=self.capacity)
        self._frontier: dict[CausalRef, tuple[str, tuple[CausalRef, ...]]] = {}
        self._subscribers: list[Callable[[CausalEvent], None]] = []
        self.emitted = 0

    # -- emission -------------------------------------------------------------
    def subscribe(self, callback: Callable[[CausalEvent], None]) -> None:
        """Outward-only observers (e.g. the lab journal); never read back."""
        self._subscribers.append(callback)

    def emit(self, event: CausalEvent) -> CausalEvent:
        self._ring.append(event)
        self.emitted += 1
        for ref in event.produced or (event.subject,):
            self._frontier[ref] = (event.event_id, event.caused_by)
        for callback in self._subscribers:
            callback(event)
        return event

    def retire(self, refs: Iterable[CausalRef]) -> None:
        """A reference is no longer live: its frontier entry may go."""
        for ref in refs:
            self._frontier.pop(ref, None)

    # -- queries --------------------------------------------------------------
    def events(self) -> tuple[CausalEvent, ...]:
        return tuple(self._ring)

    def causes_of(self, ref: CausalRef) -> tuple[CausalRef, ...] | None:
        entry = self._frontier.get(ref)
        return entry[1] if entry is not None else None

    def cause_event(self, ref: CausalRef) -> str | None:
        entry = self._frontier.get(ref)
        return entry[0] if entry is not None else None

    def live_refs(self) -> tuple[CausalRef, ...]:
        return tuple(sorted(self._frontier))

    # -- persistence ----------------------------------------------------------
    def checkpoint(self) -> dict[str, Any]:
        """The frontier only: bounded by live references, never by age."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "emitted": self.emitted,
            "frontier": [
                {
                    "ref": ref.payload(),
                    "event_id": event_id,
                    "caused_by": [cause.payload() for cause in causes],
                }
                for ref, (event_id, causes) in sorted(self._frontier.items())
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None) -> "ProvenanceLog":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported provenance checkpoint")
        log = cls(capacity=int(payload.get("capacity", RING_CAPACITY)))
        log.emitted = int(payload.get("emitted", 0))
        for raw in payload.get("frontier", []):
            log._frontier[CausalRef.from_payload(raw["ref"])] = (
                str(raw["event_id"]),
                tuple(CausalRef.from_payload(item) for item in raw["caused_by"]),
            )
        return log


__all__ = ["CausalEvent", "CausalRef", "MAX_CAUSES", "ProvenanceLog", "RING_CAPACITY"]
