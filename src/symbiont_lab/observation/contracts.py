"""Observer-only contracts exposed to presentation transports.

Nothing in this module is consumed by the organism runtime. These structures
exist solely to make the boundary between scientific evidence and UI projection
explicit and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

PRESENTATION_PROJECTION = "observer-presentation-v1"
COMPLETED_FRAME_CONTRACT = "completed-render-frame-v1"


@dataclass(frozen=True)
class ObservedFrame:
    """Coherent observer projection assembled from one completed rendered tick."""

    tick: int
    source: str
    organism_id: str | None
    body: Mapping[str, Any] | None
    cognition: Mapping[str, Any] | None
    vitals: Mapping[str, Any] | None
    mind: Mapping[str, Any]

    def as_event(self) -> dict[str, Any]:
        return {
            "type": "observed_frame",
            "source": self.source,
            "tick": int(self.tick),
            "organism_id": self.organism_id,
            "body": dict(self.body) if self.body is not None else None,
            "cognition": dict(self.cognition) if self.cognition is not None else None,
            "vitals": dict(self.vitals) if self.vitals is not None else None,
            "mind": dict(self.mind),
            "provenance": {
                "owner": "observer",
                "projection": PRESENTATION_PROJECTION,
                "contract": COMPLETED_FRAME_CONTRACT,
                "feeds_back": False,
            },
        }


__all__ = [
    "COMPLETED_FRAME_CONTRACT",
    "ObservedFrame",
    "PRESENTATION_PROJECTION",
]
