"""Durable, append-only provenance journal (Causal Provenance v1 §6).

Apparatus side: subscribes to an organism's ``ProvenanceLog`` and appends
every ``CausalEvent`` as one JSON line.  It is never read back by the
organism.  Queries reconstruct causal chains from the journal alone, so
explanations survive the organism's bounded ring wrapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

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

    def _producers(self) -> dict[CausalRef, CausalEvent]:
        producers: dict[CausalRef, CausalEvent] = {}
        for event in self.events():
            for ref in event.produced or (event.subject,):
                producers[ref] = event
        return producers

    def explain(self, ref: CausalRef) -> CausalEvent | None:
        """The event that produced ``ref``."""
        return self._producers().get(ref)

    def ancestors(self, ref: CausalRef, *, depth: int = 64) -> tuple[CausalRef, ...]:
        """Every ref reachable through ``caused_by``, breadth first, deduplicated."""
        producers = self._producers()
        seen: list[CausalRef] = []
        frontier = [ref]
        for _ in range(depth):
            following: list[CausalRef] = []
            for item in frontier:
                event = producers.get(item)
                if event is None:
                    continue
                for cause in event.caused_by:
                    if cause not in seen and cause != ref:
                        seen.append(cause)
                        following.append(cause)
            if not following:
                break
            frontier = following
        return tuple(seen)


__all__ = ["ProvenanceJournal"]
