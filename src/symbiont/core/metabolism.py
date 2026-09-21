"""Bounded organism-visible accounting for computational metabolism.

The ledger is deliberately descriptive: it does not grant or revoke host
permissions.  It turns declared work costs into finite reserve pressure that
later physiology milestones can act on.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
import math


class ResourcePressure(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    SEVERE = "severe"
    UNRECOVERABLE = "unrecoverable"


_KINDS = ("observation", "cognition", "persistence", "maintenance")


@dataclass(frozen=True, slots=True)
class MetabolicSnapshot:
    tick: int
    capacity: dict[str, float]
    reserve: dict[str, float]
    spent: dict[str, float]
    pressure: ResourcePressure


from .physiology_config import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    PhysiologyConfig,
)


class MetabolicLedger:
    """Finite, checkpointable per-tick reserve ledger.

    Reserve is replenished at the start of each tick and costs are charged
    explicitly.  Values are bounded; overdraft is retained only up to one
    capacity so pressure cannot become an unbounded accumulator.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        capacity: dict[str, float] | None = None,
        replenishment: dict[str, float] | None = None,
        reserve: dict[str, float] | None = None,
        tick: int = 0,
        physiology_config: PhysiologyConfig | None = None,
    ) -> None:
        self._config = physiology_config or DEFAULT_PHYSIOLOGY_CONFIG
        self._capacity = self._validate(
            capacity or {k: 1.0 for k in _KINDS},
            "capacity",
            positive=True,
        )
        self._replenishment = self._validate(
            replenishment or self._capacity,
            "replenishment",
            positive=False,
        )
        initial = self._capacity if reserve is None else reserve
        self._reserve = self._validate(
            initial,
            "reserve",
            positive=False,
            allow_negative=True,
        )
        self._reserve = {k: max(-self._capacity[k], min(self._capacity[k], self._reserve[k])) for k in _KINDS}
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        self._tick = tick
        self._spent = {k: 0.0 for k in _KINDS}

    @staticmethod
    def _validate(
        values: dict[str, float],
        label: str,
        *,
        positive: bool,
        allow_negative: bool = False,
    ) -> dict[str, float]:
        if set(values) != set(_KINDS):
            raise ValueError(f"{label} must define exactly {_KINDS}")
        if any(isinstance(values[k], bool) or not isinstance(values[k], (int, float)) for k in _KINDS):
            raise ValueError(f"{label} values must be numeric")
        result = {k: float(values[k]) for k in _KINDS}
        if any(not math.isfinite(v) for v in result.values()):
            raise ValueError(f"{label} values must be finite")
        if positive:
            if any(v <= 0.0 for v in result.values()):
                raise ValueError(f"{label} values out of bounds")
        elif not allow_negative and any(v < 0.0 for v in result.values()):
            raise ValueError(f"{label} values out of bounds")
        return result

    @property
    def tick(self) -> int:
        return self._tick

    def charge(self, kind: str, amount: float) -> None:
        if kind not in _KINDS:
            raise ValueError(f"unknown metabolic cost kind: {kind}")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
            raise ValueError("metabolic charge must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("metabolic charge must be non-negative")
        self._spent[kind] = min(self._capacity[kind] * 2.0, self._spent[kind] + amount)
        self._reserve[kind] = max(-self._capacity[kind], self._reserve[kind] - amount)

    def intake(self, kind: str, amount: float) -> float:
        """Add explicitly acquired resource and return the accepted amount.

        Intake is the only way to replenish a ledger configured with zero
        automatic replenishment; it is bounded by capacity and never creates
        resource above that capacity.
        """
        if kind not in _KINDS:
            raise ValueError(f"unknown metabolic resource kind: {kind}")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
            raise ValueError("metabolic intake must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("metabolic intake must be non-negative")
        accepted = min(amount, self._capacity[kind] - self._reserve[kind])
        self._reserve[kind] += accepted
        return accepted

    def advance(self, *, retained_units: float = 0.0) -> MetabolicSnapshot:
        if (isinstance(retained_units, bool) or not isinstance(retained_units, (int, float))
                or not math.isfinite(retained_units) or retained_units < 0.0):
            raise ValueError("retained_units must be finite and non-negative")
        for kind in _KINDS:
            self._reserve[kind] = min(self._capacity[kind], self._reserve[kind] + self._replenishment[kind])
        self.charge("maintenance", retained_units)
        self._tick += 1
        snapshot = self.snapshot()
        self._spent = {k: 0.0 for k in _KINDS}
        return snapshot

    @property
    def physiology_config(self) -> PhysiologyConfig:
        return self._config

    def pressure(self) -> ResourcePressure:
        ratio = min(self._reserve[k] / self._capacity[k] for k in _KINDS)
        if ratio < self._config.ratio_unrecoverable:
            return ResourcePressure.UNRECOVERABLE
        if ratio < self._config.ratio_severe:
            return ResourcePressure.SEVERE
        if ratio < self._config.ratio_elevated:
            return ResourcePressure.ELEVATED
        return ResourcePressure.NORMAL

    def snapshot(self) -> MetabolicSnapshot:
        return MetabolicSnapshot(self._tick, dict(self._capacity), dict(self._reserve), dict(self._spent), self.pressure())

    def checkpoint(self) -> dict[str, Any]:
        return {"schema_version": self.SCHEMA_VERSION, "tick": self._tick,
                "capacity": dict(self._capacity), "replenishment": dict(self._replenishment),
                "reserve": dict(self._reserve)}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], *, physiology_config: PhysiologyConfig | None = None) -> "MetabolicLedger":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid metabolic checkpoint")
        tick = payload.get("tick")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("invalid metabolic checkpoint tick")
        return cls(capacity=payload["capacity"], replenishment=payload["replenishment"],
                   reserve=payload["reserve"], tick=tick, physiology_config=physiology_config)


__all__ = ["MetabolicLedger", "MetabolicSnapshot", "ResourcePressure"]
