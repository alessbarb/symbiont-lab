"""Durable, append-only provenance journal (Causal Provenance v1 §6).

Apparatus side: subscribes to an organism's ``ProvenanceLog`` and appends
every ``CausalEvent`` as one JSON line.  It is never read back by the
organism.  Queries reconstruct causal chains from the journal alone, so
explanations survive the organism's bounded ring wrapping.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from symbiont.provenance import CausalEvent, CausalRef


class ProvenanceJournal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: CausalEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.payload(), sort_keys=True) + "\n")

    def events(self) -> Iterator[CausalEvent]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield CausalEvent.from_payload(json.loads(line))

    def explain(self, ref: CausalRef) -> CausalEvent | None:
        """The event that produced ``ref``."""
        return ProvenanceIndex.load(self).producers.get(ref)

    def ancestors(self, ref: CausalRef, *, depth: int = 64) -> tuple[CausalRef, ...]:
        """Every ref reachable through ``caused_by``, breadth first, deduplicated."""
        return ProvenanceIndex.load(self).ancestors(ref, depth=depth)


class ProvenanceIndex:
    """Chain queries over one journal, loaded once (apparatus side only)."""

    def __init__(self, events: Iterable[CausalEvent]) -> None:
        self.events: tuple[CausalEvent, ...] = tuple(events)
        # A ref's lifecycle (e.g. intent form ... satisfied) may span several
        # events; its causes are the union over all of them.
        self.lifecycle: dict[CausalRef, list[CausalEvent]] = {}
        for event in self.events:
            for ref in event.produced or (event.subject,):
                self.lifecycle.setdefault(ref, []).append(event)
        self.producers: dict[CausalRef, CausalEvent] = {
            ref: events[-1] for ref, events in self.lifecycle.items()
        }

    @classmethod
    def load(cls, journal: "ProvenanceJournal") -> "ProvenanceIndex":
        return cls(journal.events())

    def find(
        self, *, domain: str | None = None, operation: str | None = None, kind: str | None = None
    ) -> tuple[CausalEvent, ...]:
        return tuple(
            event
            for event in self.events
            if (domain is None or event.domain == domain)
            and (operation is None or event.operation == operation)
            and (kind is None or event.subject.kind == kind)
        )

    def summary(self) -> dict[str, int]:
        counts = Counter(f"{event.domain}.{event.operation}" for event in self.events)
        return dict(sorted(counts.items()))

    def causes(self, ref: CausalRef) -> tuple[CausalRef, ...]:
        """Distinct causes of ``ref`` across its whole lifecycle, first seen first."""
        seen: dict[CausalRef, None] = {}
        for event in self.lifecycle.get(ref, ()):
            for cause in event.caused_by:
                if cause != ref:
                    seen.setdefault(cause)
        return tuple(seen)

    def why(self, ref: CausalRef, *, depth: int = 12) -> dict[str, Any]:
        """The causal tree behind ``ref`` (each ref expanded once; roots marked)."""
        seen: set[CausalRef] = set()

        def node(item: CausalRef, level: int) -> dict[str, Any]:
            event = self.producers.get(item)
            entry: dict[str, Any] = {"ref": item.payload()}
            if event is None:
                entry["root"] = True  # raw evidence or outside the journal
                return entry
            entry["event"] = {
                "tick": event.tick,
                "domain": event.domain,
                "operation": event.operation,
                "rule": event.rule,
                "parameters": dict(event.parameters),
            }
            if item in seen:
                entry["repeated"] = True
                return entry
            seen.add(item)
            if level >= depth:
                entry["truncated"] = True
                return entry
            entry["causes"] = [node(cause, level + 1) for cause in self.causes(item)]
            return entry

        return node(ref, 0)

    def reaches(self, ref: CausalRef, kind: str, *, depth: int = 32) -> bool:
        """Whether ``ref`` has an ancestor of ``kind`` (e.g. pulse commitments)."""
        return any(item.kind == kind for item in self.ancestors(ref, depth=depth))

    def ancestors(self, ref: CausalRef, *, depth: int = 32) -> tuple[CausalRef, ...]:
        seen: list[CausalRef] = []
        frontier = [ref]
        for _ in range(depth):
            following: list[CausalRef] = []
            for item in frontier:
                for cause in self.causes(item):
                    if cause not in seen and cause != ref:
                        seen.append(cause)
                        following.append(cause)
            if not following:
                break
            frontier = following
        return tuple(seen)


def render_tree(tree: Mapping[str, Any], *, indent: int = 0) -> list[str]:
    """Human-readable lines for a ``ProvenanceIndex.why`` tree."""
    kind, ref_id = tree["ref"]
    pad = "  " * indent
    event = tree.get("event")
    if event is None:
        line = f"{pad}{kind}:{ref_id}  [root]"
    else:
        rule = f" rule={event['rule']}" if event["rule"] else ""
        line = f"{pad}{kind}:{ref_id}  <- {event['domain']}.{event['operation']} @t{event['tick']}{rule}"
        if tree.get("repeated"):
            line += "  (see above)"
        if tree.get("truncated"):
            line += "  (truncated)"
    lines = [line]
    for cause in tree.get("causes", ()):
        lines.extend(render_tree(cause, indent=indent + 1))
    return lines


__all__ = ["ProvenanceIndex", "ProvenanceJournal", "render_tree"]
