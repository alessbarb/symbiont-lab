"""Constitutive bodily homeostasis and physiological activity regulation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
import math

from .metabolism import MetabolicLedger, ResourcePressure


class HomeostaticAction(StrEnum):
    MAINTAIN = "maintain"
    REDUCE_ACTIVITY = "reduce_activity"
    PAUSE_PLASTICITY = "pause_plasticity"
    SAFE_MODE = "safe_mode"


@dataclass(frozen=True, slots=True)
class HomeostaticSnapshot:
    integrity: float
    activity_scale: float
    plasticity_enabled: bool
    action: HomeostaticAction


from .physiology import LivingBodyState, PhysiologyConfig, DEFAULT_PHYSIOLOGY_CONFIG


class HomeostaticController:
    """Kernel-bounded response to metabolic pressure and local damage."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        integrity: float = 1.0,
        activity_scale: float = 1.0,
        plasticity_enabled: bool = True,
        config: PhysiologyConfig | None = None,
        body_state: LivingBodyState | None = None,
    ) -> None:
        if not 0.0 <= integrity <= 1.0 or not 0.0 < activity_scale <= 1.0:
            raise ValueError("homeostatic values out of bounds")
        if body_state is None:
            body_state = LivingBodyState(structural_integrity=float(integrity))
        elif integrity != 1.0 and float(integrity) != body_state.structural_integrity:
            raise ValueError("homeostatic integrity contradicts living body state")
        self._body_state = body_state
        self.activity_scale = float(activity_scale)
        self.plasticity_enabled = bool(plasticity_enabled)
        self.config = config or DEFAULT_PHYSIOLOGY_CONFIG

    @property
    def body_state(self) -> LivingBodyState:
        return self._body_state

    @property
    def integrity(self) -> float:
        return self._body_state.structural_integrity

    @integrity.setter
    def integrity(self, value: float) -> None:
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError("integrity out of bounds")
        # Routed through the delta-based writer (not a direct field set) so
        # a body with structure_states keeps every structure in sync with
        # the aggregate rather than going stale (L5.5.1).
        self._body_state.apply_structural_delta(value - self._body_state.structural_integrity)

    def deviation(self) -> float:
        """Return constitutional physiological disequilibrium in [0, 1].

        This is innate valence, not semantic reward. It exposes no field names
        to cognition and contains no environmental target. A value of zero means
        the body is near its viable set; larger values mean at least one
        internally owned physiological variable is farther from viability.
        """
        energy_deficit = 1.0 - (
            self._body_state.energy_reserve
            / max(self._body_state.max_energy, 1e-12)
        )
        integrity_deficit = 1.0 - self._body_state.structural_integrity
        thermal_span = max(
            self.config.thermal_setpoint,
            1.0 - self.config.thermal_setpoint,
            1e-12,
        )
        thermal_deviation = abs(
            self._body_state.temperature - self.config.thermal_setpoint
        ) / thermal_span
        fatigue = self._body_state.fatigue
        return max(
            0.0,
            min(
                1.0,
                max(
                    energy_deficit,
                    integrity_deficit,
                    thermal_deviation,
                    fatigue,
                ),
            ),
        )

    def constitutive_step(
        self,
        metabolism: MetabolicLedger,
        *,
        embodied_work: float = 0.0,
        resting: bool = False,
    ) -> float:
        """Advance innate body homeostasis without cognitive instruction.

        Physical work raises fatigue and temperature. Inactivity recovers
        fatigue and temperature relaxes toward the constitutional setpoint.
        Damaged tissue repairs automatically when maintenance reserve exists.
        The returned value is repaired integrity, for passive telemetry only.
        """
        embodied_work = float(embodied_work)
        if not math.isfinite(embodied_work) or embodied_work < 0.0:
            raise ValueError("embodied_work must be finite and non-negative")

        fatigue_gain = min(1.0, embodied_work * self.config.fatigue_work_gain)
        recovery = self.config.fatigue_recovery_rate * (2.0 if resting else 1.0)
        self._body_state.fatigue = max(
            0.0,
            min(1.0, self._body_state.fatigue + fatigue_gain - recovery),
        )

        target = self.config.thermal_setpoint
        relaxed = self._body_state.temperature + (
            target - self._body_state.temperature
        ) * self.config.thermal_relaxation_rate
        heated = relaxed + embodied_work * self.config.thermal_work_gain
        self._body_state.temperature = max(0.0, min(1.0, heated))

        if self.integrity >= 1.0:
            return 0.0
        available = min(
            max(0.0, metabolism.snapshot().reserve["maintenance"]),
            max(0.0, self._body_state.energy_reserve),
        )
        repair = min(
            1.0 - self.integrity,
            self.config.autonomous_repair_rate,
            available,
        )
        if repair <= 0.0:
            return 0.0
        metabolism.charge("maintenance", repair)
        self.integrity = min(1.0, self.integrity + repair)
        return repair

    def regulate(self, pressure: ResourcePressure) -> HomeostaticSnapshot:
        if not isinstance(pressure, ResourcePressure):
            pressure = ResourcePressure(str(pressure))
        action = HomeostaticAction.MAINTAIN
        if pressure is ResourcePressure.ELEVATED:
            self.activity_scale = max(self.config.activity_elevated_floor, self.activity_scale * self.config.activity_elevated_penalty)
            action = HomeostaticAction.REDUCE_ACTIVITY
        elif pressure is ResourcePressure.SEVERE:
            self.activity_scale = max(self.config.activity_severe_floor, self.activity_scale * self.config.activity_severe_penalty)
            self.plasticity_enabled = False
            action = HomeostaticAction.PAUSE_PLASTICITY
        elif pressure is ResourcePressure.UNRECOVERABLE or self.integrity <= self.config.safe_mode_integrity_threshold:
            self.activity_scale = self.config.safe_mode_activity_scale
            self.plasticity_enabled = False
            action = HomeostaticAction.SAFE_MODE
        elif pressure is ResourcePressure.NORMAL and self.integrity >= 0.8:
            self.activity_scale = min(1.0, self.activity_scale + 0.05)
            self.plasticity_enabled = True

        if self._body_state.fatigue > self.config.fatigue_activity_threshold:
            span = max(1e-12, 1.0 - self.config.fatigue_activity_threshold)
            excess = (
                self._body_state.fatigue - self.config.fatigue_activity_threshold
            ) / span
            fatigue_scale = 1.0 - excess * (
                1.0 - self.config.fatigue_activity_floor
            )
            self.activity_scale = min(
                self.activity_scale,
                max(self.config.fatigue_activity_floor, fatigue_scale),
            )
            if action is HomeostaticAction.MAINTAIN:
                action = HomeostaticAction.REDUCE_ACTIVITY
        return HomeostaticSnapshot(self.integrity, self.activity_scale, self.plasticity_enabled, action)


    def checkpoint(self) -> dict[str, Any]:
        return {"schema_version": self.SCHEMA_VERSION, "integrity": self.integrity,
                "activity_scale": self.activity_scale, "plasticity_enabled": self.plasticity_enabled}

    @classmethod
    def from_checkpoint(
        cls,
        payload: dict[str, Any],
        *,
        config: PhysiologyConfig | None = None,
        body_state: LivingBodyState | None = None,
    ) -> "HomeostaticController":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid homeostatic checkpoint")
        integrity = float(payload["integrity"])
        if body_state is not None and body_state.structural_integrity != integrity:
            raise ValueError("homeostasis checkpoint contradicts living body state")
        return cls(
            integrity=integrity,
            activity_scale=float(payload["activity_scale"]),
            plasticity_enabled=payload["plasticity_enabled"],
            config=config,
            body_state=body_state,
        )


__all__ = ["HomeostaticAction", "HomeostaticController", "HomeostaticSnapshot"]
