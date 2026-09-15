"""Homeostatic effort allocation and local repair (v0.63)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .metabolism import MetabolicLedger, ResourcePressure


class HomeostaticAction(StrEnum):
    MAINTAIN = "maintain"
    REDUCE_ACTIVITY = "reduce_activity"
    PAUSE_PLASTICITY = "pause_plasticity"
    REPAIR = "repair"
    SAFE_MODE = "safe_mode"


@dataclass(frozen=True, slots=True)
class HomeostaticSnapshot:
    integrity: float
    activity_scale: float
    plasticity_enabled: bool
    action: HomeostaticAction


class HomeostaticController:
    """Kernel-bounded response to metabolic pressure and local damage."""

    SCHEMA_VERSION = 1

    def __init__(self, *, integrity: float = 1.0, activity_scale: float = 1.0,
                 plasticity_enabled: bool = True) -> None:
        if not 0.0 <= integrity <= 1.0 or not 0.0 < activity_scale <= 1.0:
            raise ValueError("homeostatic values out of bounds")
        self.integrity = float(integrity)
        self.activity_scale = float(activity_scale)
        self.plasticity_enabled = bool(plasticity_enabled)

    def regulate(self, pressure: ResourcePressure, *, repairable_damage: float = 0.0) -> HomeostaticSnapshot:
        if not isinstance(pressure, ResourcePressure):
            pressure = ResourcePressure(str(pressure))
        if not 0.0 <= repairable_damage <= 1.0:
            raise ValueError("repairable_damage must be within [0, 1]")
        action = HomeostaticAction.MAINTAIN
        if repairable_damage > 0.0 and self.integrity < 1.0:
            repaired = min(repairable_damage, 0.25)
            self.integrity = min(1.0, self.integrity + repaired)
            action = HomeostaticAction.REPAIR
        if pressure is ResourcePressure.ELEVATED:
            self.activity_scale = max(0.5, self.activity_scale * 0.9)
            action = HomeostaticAction.REDUCE_ACTIVITY
        elif pressure is ResourcePressure.SEVERE:
            self.activity_scale = max(0.2, self.activity_scale * 0.75)
            self.plasticity_enabled = False
            action = HomeostaticAction.PAUSE_PLASTICITY
        elif pressure is ResourcePressure.UNRECOVERABLE or self.integrity <= 0.1:
            self.activity_scale = 0.1
            self.plasticity_enabled = False
            action = HomeostaticAction.SAFE_MODE
        elif pressure is ResourcePressure.NORMAL and self.integrity >= 0.8:
            self.activity_scale = min(1.0, self.activity_scale + 0.05)
            self.plasticity_enabled = True
        return HomeostaticSnapshot(self.integrity, self.activity_scale, self.plasticity_enabled, action)

    def repair_with_resources(self, metabolism: MetabolicLedger, requested: float) -> float:
        """Repair integrity by charging maintenance, bounded by available reserve."""
        requested = float(requested)
        if requested < 0.0 or requested > 1.0:
            raise ValueError("requested repair must be within [0, 1]")
        if self.integrity >= 1.0 or requested == 0.0:
            return 0.0
        # One integrity unit costs one maintenance unit; no free repair.
        available = max(0.0, metabolism.snapshot().reserve["maintenance"])
        repaired = min(requested, 0.25, available)
        if repaired:
            metabolism.charge("maintenance", repaired)
            self.integrity = min(1.0, self.integrity + repaired)
        return repaired

    def checkpoint(self) -> dict[str, Any]:
        return {"schema_version": self.SCHEMA_VERSION, "integrity": self.integrity,
                "activity_scale": self.activity_scale, "plasticity_enabled": self.plasticity_enabled}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "HomeostaticController":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid homeostatic checkpoint")
        return cls(integrity=float(payload["integrity"]), activity_scale=float(payload["activity_scale"]),
                   plasticity_enabled=payload["plasticity_enabled"])


__all__ = ["HomeostaticAction", "HomeostaticController", "HomeostaticSnapshot"]
