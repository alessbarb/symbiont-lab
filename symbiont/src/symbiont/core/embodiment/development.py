"""Derived ontogenetic observations for the organism lifecycle.

Developmental phase is descriptive state, not a timer-driven controller.  It
is derived from viability, cognitive topology, sensory development, action
experience and accumulated stress.  Nothing in this module schedules an
action or grants a capability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class DevelopmentalPhase(StrEnum):
    GERMINAL = "germinal"
    DEVELOPING = "developing"
    JUVENILE = "juvenile"
    MATURE = "mature"
    DECLINING = "declining"
    TERMINAL = "terminal"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class DevelopmentalSnapshot:
    phase: DevelopmentalPhase
    tick: int
    stress_ticks: int
    recovery_events: int
    repair_events: int
    excretion_events: int
    maintenance_burden: float
    senescence_index: float
    action_attempts: int
    sensory_count: int
    topology_health: str


class DevelopmentalTracker:
    """Bounded history used only to derive a lifecycle classification."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        tick: int = 0,
        stress_ticks: int = 0,
        recovery_events: int = 0,
        previous_stressed: bool = False,
        repair_events: int = 0,
        excretion_events: int = 0,
        maintenance_burden: float = 0.0,
        retention_burden: float = 0.0,
    ) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (tick, stress_ticks, recovery_events, repair_events, excretion_events)
        ):
            raise ValueError("development counters must be non-negative integers")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
            for value in (maintenance_burden, retention_burden)
        ):
            raise ValueError("development burdens must be within [0, 1]")
        self._tick = tick
        self._stress_ticks = min(stress_ticks, 1_000_000)
        self._recovery_events = min(recovery_events, 1_000_000)
        self._repair_events = min(repair_events, 1_000_000)
        self._excretion_events = min(excretion_events, 1_000_000)
        self._maintenance_burden = float(maintenance_burden)
        self._retention_burden = float(retention_burden)
        self._previous_stressed = bool(previous_stressed)

    def observe(
        self,
        *,
        state: str,
        integrity: float,
        topology_health: str,
        sensory_count: int,
        action_attempts: int,
        maintenance_ratio: float = 0.0,
        retained_items: int = 0,
        degradation_excreted: int = 0,
        repaired: bool = False,
        plasticity_enabled: bool = True,
    ) -> DevelopmentalSnapshot:
        if not isinstance(state, str) or not state:
            raise ValueError("development state must be non-empty")
        if not isinstance(topology_health, str) or not topology_health:
            raise ValueError("topology health must be non-empty")
        if (
            isinstance(integrity, bool)
            or not isinstance(integrity, (int, float))
            or not math.isfinite(float(integrity))
            or not 0.0 <= integrity <= 1.0
        ):
            raise ValueError("integrity must be within [0, 1]")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (sensory_count, action_attempts)
        ):
            raise ValueError("development observations must be non-negative integers")
        if (
            isinstance(maintenance_ratio, bool)
            or not isinstance(maintenance_ratio, (int, float))
            or not math.isfinite(float(maintenance_ratio))
            or not 0.0 <= maintenance_ratio <= 1.0
        ):
            raise ValueError("maintenance_ratio must be within [0, 1]")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (retained_items, degradation_excreted)
        ):
            raise ValueError("retention observations must be non-negative integers")
        if not isinstance(repaired, bool) or not isinstance(plasticity_enabled, bool):
            raise ValueError("repair and plasticity observations must be boolean")

        stressed = state in {"stressed", "agonizing", "dormant"}
        if stressed:
            self._stress_ticks = min(1_000_000, self._stress_ticks + 1)
        if self._previous_stressed and state == "active":
            self._recovery_events = min(1_000_000, self._recovery_events + 1)
        self._previous_stressed = stressed
        self._maintenance_burden = 0.8 * self._maintenance_burden + 0.2 * float(maintenance_ratio)
        self._retention_burden = 0.8 * self._retention_burden + 0.2 * min(
            1.0, retained_items / 64.0
        )
        self._repair_events = min(1_000_000, self._repair_events + int(repaired))
        self._excretion_events = min(
            1_000_000, self._excretion_events + min(degradation_excreted, 1_000_000)
        )
        self._tick = min(1_000_000_000, self._tick + 1)
        senescence_index = min(
            1.0,
            max(
                0.0,
                (
                    0.35 * self._maintenance_burden
                    + 0.25 * self._retention_burden
                    + 0.20 * min(1.0, self._excretion_events / 16.0)
                    + 0.20 * (1.0 - float(integrity))
                ),
            ),
        )

        if state == "dead":
            phase = DevelopmentalPhase.DEAD
        elif state == "agonizing" or integrity <= 0.15:
            phase = DevelopmentalPhase.TERMINAL
        elif (
            integrity < 0.8
            and (self._stress_ticks >= 8 or senescence_index >= 0.55)
            and (not plasticity_enabled or self._repair_events >= 2 or self._excretion_events >= 4)
        ):
            phase = DevelopmentalPhase.DECLINING
        elif self._tick == 1 and topology_health == "germinal" and sensory_count == 0:
            phase = DevelopmentalPhase.GERMINAL
        elif topology_health in {"germinal", "developing", "recovering"} or sensory_count < 2:
            phase = DevelopmentalPhase.DEVELOPING
        elif topology_health == "adaptive" and action_attempts >= 8:
            phase = DevelopmentalPhase.MATURE
        else:
            phase = DevelopmentalPhase.JUVENILE
        return DevelopmentalSnapshot(
            phase,
            self._tick,
            self._stress_ticks,
            self._recovery_events,
            self._repair_events,
            self._excretion_events,
            round(self._maintenance_burden, 6),
            round(senescence_index, 6),
            min(action_attempts, 1_000_000),
            min(sensory_count, 1_000_000),
            topology_health[:64],
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "tick": self._tick,
            "stress_ticks": self._stress_ticks,
            "recovery_events": self._recovery_events,
            "repair_events": self._repair_events,
            "excretion_events": self._excretion_events,
            "maintenance_burden": self._maintenance_burden,
            "retention_burden": self._retention_burden,
            "previous_stressed": self._previous_stressed,
        }

    @classmethod
    def from_checkpoint(cls, payload: object) -> "DevelopmentalTracker":
        if not isinstance(payload, dict) or payload.get("schema_version") not in (
            1,
            cls.SCHEMA_VERSION,
        ):
            raise ValueError("invalid developmental checkpoint")
        return cls(
            tick=payload.get("tick", 0),
            stress_ticks=payload.get("stress_ticks", 0),
            recovery_events=payload.get("recovery_events", 0),
            repair_events=payload.get("repair_events", 0),
            excretion_events=payload.get("excretion_events", 0),
            maintenance_burden=payload.get("maintenance_burden", 0.0),
            retention_burden=payload.get("retention_burden", 0.0),
            previous_stressed=payload.get("previous_stressed", False),
        )


__all__ = ["DevelopmentalPhase", "DevelopmentalSnapshot", "DevelopmentalTracker"]
