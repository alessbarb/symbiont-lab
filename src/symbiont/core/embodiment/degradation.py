"""Bounded lifecycle for low-value retained state (v0.62)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RetentionState(StrEnum):
    ACTIVE = "active"
    AGING = "aging"
    WASTE = "waste"
    EXCRETED = "excreted"


@dataclass(slots=True)
class RetainedItem:
    item_id: str
    value: float
    age: int = 0
    state: RetentionState = RetentionState.ACTIVE


from ..foundation.limits import OrganismLimits
from .physiology import DEFAULT_PHYSIOLOGY_CONFIG

_DEFAULT_MAX_ITEMS = OrganismLimits().max_degradation_items
_DEFAULT_AGING_TICKS = DEFAULT_PHYSIOLOGY_CONFIG.aging_ticks
_DEFAULT_WASTE_TICKS = DEFAULT_PHYSIOLOGY_CONFIG.waste_ticks


class DegradationQueue:
    """Age, demote and irreversibly excrete bounded abstract state."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        max_items: int = _DEFAULT_MAX_ITEMS,
        aging_ticks: int = _DEFAULT_AGING_TICKS,
        waste_ticks: int = _DEFAULT_WASTE_TICKS,
    ) -> None:
        if min(max_items, aging_ticks, waste_ticks) < 1:
            raise ValueError("degradation limits must be positive")
        self.max_items, self.aging_ticks, self.waste_ticks = max_items, aging_ticks, waste_ticks
        self._items: dict[str, RetainedItem] = {}
        self.excreted_units = 0

    @property
    def items(self) -> tuple[RetainedItem, ...]:
        return tuple(self._items.values())

    def retain(self, item_id: str, value: float) -> bool:
        if not item_id or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("item_id and value are invalid")
        if item_id not in self._items and len(self._items) >= self.max_items:
            return False
        self._items[item_id] = RetainedItem(item_id, float(value))
        return True

    def age_tick(self) -> int:
        for item in self._items.values():
            if item.state is RetentionState.EXCRETED:
                continue
            item.age += 1
            if item.state is RetentionState.ACTIVE and item.age >= self.aging_ticks:
                item.state = RetentionState.AGING
            if (
                item.state is RetentionState.AGING
                and item.age >= self.aging_ticks + self.waste_ticks
            ):
                item.state = RetentionState.WASTE
        return self._excrete_waste()

    def _excrete_waste(self) -> int:
        ids = [
            item_id for item_id, item in self._items.items() if item.state is RetentionState.WASTE
        ]
        for item_id in ids:
            self._items[item_id].state = RetentionState.EXCRETED
            self.excreted_units += 1
            del self._items[item_id]
        return len(ids)

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "max_items": self.max_items,
            "aging_ticks": self.aging_ticks,
            "waste_ticks": self.waste_ticks,
            "excreted_units": self.excreted_units,
            "items": [
                {"item_id": i.item_id, "value": i.value, "age": i.age, "state": i.state.value}
                for i in self.items
            ],
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "DegradationQueue":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid degradation checkpoint")
        q = cls(
            max_items=int(payload["max_items"]),
            aging_ticks=int(payload["aging_ticks"]),
            waste_ticks=int(payload["waste_ticks"]),
        )
        q.excreted_units = int(payload.get("excreted_units", 0))
        for raw in payload.get("items", []):
            if not isinstance(raw, dict) or raw.get("state") == RetentionState.EXCRETED.value:
                raise ValueError("invalid degradation item")
            q._items[raw["item_id"]] = RetainedItem(
                raw["item_id"], float(raw["value"]), int(raw["age"]), RetentionState(raw["state"])
            )
        if len(q._items) > q.max_items:
            raise ValueError("degradation checkpoint exceeds max_items")
        return q


__all__ = ["DegradationQueue", "RetentionState", "RetainedItem"]
