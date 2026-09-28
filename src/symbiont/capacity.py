"""Capacity pressure of bounded stores (Cross-Domain Revision Coherence v1 §2.1).

Measurement only. A store notes an eviction *after* its existing policy has
chosen and applied it, and notes an admission after inserting a new item.
Nothing here is read by any decision, so instrumenting a store never changes
behaviour. Evicted items are remembered by a short one-way fingerprint so a
later reappearance counts as ``relearned_after_eviction``; the fingerprints
are never used as functional memory.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Iterable, Mapping

RECENT_EVICTIONS = 256


def _fingerprint(item_ref: str) -> str:
    return hashlib.sha256(item_ref.encode("utf-8")).hexdigest()[:16]


class CapacityPressure:
    SCHEMA_VERSION = 1

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self.evictions = 0
        self.admissions = 0
        self.promotions = 0
        self.demotions = 0
        self.relearned_after_eviction = 0
        self._recently_evicted: OrderedDict[str, None] = OrderedDict()

    def note_evicted(self, item_refs: Iterable[str]) -> None:
        for item_ref in item_refs:
            self.evictions += 1
            key = _fingerprint(str(item_ref))
            self._recently_evicted[key] = None
            self._recently_evicted.move_to_end(key)
            while len(self._recently_evicted) > RECENT_EVICTIONS:
                self._recently_evicted.popitem(last=False)

    def note_admitted(self, item_ref: str) -> None:
        self.admissions += 1
        key = _fingerprint(str(item_ref))
        if key in self._recently_evicted:
            del self._recently_evicted[key]
            self.relearned_after_eviction += 1

    def snapshot(self, occupancy: int) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "occupancy": int(occupancy),
            "pressure": int(occupancy) / self.capacity,
            "admissions": self.admissions,
            "evictions": self.evictions,
            "promotions": self.promotions,
            "demotions": self.demotions,
            "relearned_after_eviction": self.relearned_after_eviction,
        }

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "admissions": self.admissions,
            "evictions": self.evictions,
            "promotions": self.promotions,
            "demotions": self.demotions,
            "relearned_after_eviction": self.relearned_after_eviction,
            "recently_evicted": list(self._recently_evicted),
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None, *, capacity: int) -> "CapacityPressure":
        """Absent in checkpoints older than Wave 0: counting starts fresh."""
        pressure = cls(capacity)
        if not isinstance(payload, Mapping):
            return pressure
        for name in ("admissions", "evictions", "promotions", "demotions"):
            setattr(pressure, name, max(0, int(payload.get(name, 0))))
        pressure.relearned_after_eviction = max(0, int(payload.get("relearned_after_eviction", 0)))
        for key in list(payload.get("recently_evicted", ()))[-RECENT_EVICTIONS:]:
            pressure._recently_evicted[str(key)] = None
        return pressure


__all__ = ["CapacityPressure", "RECENT_EVICTIONS"]
