"""Canonical physiology configuration and metabolic dynamics.

Defines immutable thresholds, rates, and parameters for organism viability,
homeostatic response, and computational metabolism.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class PhysiologyConfig:
    """Immutable physiological thresholds, metabolic ratios and temporal rates.

    Controls 'when does it change?', 'at what rate?' and 'what state does it enter?'.
    Never altered via environment variables in a live organism to preserve
    strict scientific reproducibility.
    """

    ratio_unrecoverable: float = 0.0
    ratio_severe: float = 0.2
    ratio_elevated: float = 0.5
    max_repair_per_tick: float = 0.25
    autonomous_repair_rate: float = 0.02
    fatigue_work_gain: float = 0.50
    fatigue_recovery_rate: float = 0.02
    fatigue_activity_threshold: float = 0.50
    fatigue_activity_floor: float = 0.20
    thermal_setpoint: float = 0.50
    thermal_relaxation_rate: float = 0.02
    thermal_work_gain: float = 0.10
    activity_elevated_penalty: float = 0.9
    activity_elevated_floor: float = 0.5
    activity_severe_penalty: float = 0.75
    activity_severe_floor: float = 0.2
    safe_mode_integrity_threshold: float = 0.1
    safe_mode_activity_scale: float = 0.1
    aging_ticks: int = 16
    waste_ticks: int = 8
    dormant_metabolic_factor: float = 0.25

    def __post_init__(self) -> None:
        # Check no bools masquerading as numeric
        for field_name in (
            "ratio_unrecoverable",
            "ratio_severe",
            "ratio_elevated",
            "max_repair_per_tick",
            "autonomous_repair_rate",
            "fatigue_work_gain",
            "fatigue_recovery_rate",
            "fatigue_activity_threshold",
            "fatigue_activity_floor",
            "thermal_setpoint",
            "thermal_relaxation_rate",
            "thermal_work_gain",
            "activity_elevated_penalty",
            "activity_elevated_floor",
            "activity_severe_penalty",
            "activity_severe_floor",
            "safe_mode_integrity_threshold",
            "safe_mode_activity_scale",
            "dormant_metabolic_factor",
            "aging_ticks",
            "waste_ticks",
        ):
            val = getattr(self, field_name)
            if isinstance(val, bool):
                raise ValueError(f"{field_name} must be numeric, not bool")

        # Finite checks
        for field_name in (
            "ratio_unrecoverable",
            "ratio_severe",
            "ratio_elevated",
            "max_repair_per_tick",
            "autonomous_repair_rate",
            "fatigue_work_gain",
            "fatigue_recovery_rate",
            "fatigue_activity_threshold",
            "fatigue_activity_floor",
            "thermal_setpoint",
            "thermal_relaxation_rate",
            "thermal_work_gain",
            "activity_elevated_penalty",
            "activity_elevated_floor",
            "activity_severe_penalty",
            "activity_severe_floor",
            "safe_mode_integrity_threshold",
            "safe_mode_activity_scale",
            "dormant_metabolic_factor",
        ):
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"{field_name} must be a finite float")

        # Ratio hierarchy
        if not (self.ratio_unrecoverable <= self.ratio_severe <= self.ratio_elevated):
            raise ValueError(
                f"ratios must satisfy ratio_unrecoverable <= ratio_severe <= ratio_elevated; "
                f"got {self.ratio_unrecoverable} <= {self.ratio_severe} <= {self.ratio_elevated}"
            )

        # Repair rate
        if self.max_repair_per_tick <= 0.0:
            raise ValueError(f"max_repair_per_tick must be positive; got {self.max_repair_per_tick}")

        if not 0.0 < self.autonomous_repair_rate <= self.max_repair_per_tick:
            raise ValueError("autonomous_repair_rate must be within (0, max_repair_per_tick]")
        if not 0.0 <= self.fatigue_work_gain <= 1.0:
            raise ValueError("fatigue_work_gain must be within [0, 1]")
        if not 0.0 <= self.fatigue_recovery_rate <= 1.0:
            raise ValueError("fatigue_recovery_rate must be within [0, 1]")
        if not 0.0 <= self.fatigue_activity_threshold <= 1.0:
            raise ValueError("fatigue_activity_threshold must be within [0, 1]")
        if not 0.0 < self.fatigue_activity_floor <= 1.0:
            raise ValueError("fatigue_activity_floor must be within (0, 1]")
        if not 0.0 <= self.thermal_setpoint <= 1.0:
            raise ValueError("thermal_setpoint must be within [0, 1]")
        if not 0.0 <= self.thermal_relaxation_rate <= 1.0:
            raise ValueError("thermal_relaxation_rate must be within [0, 1]")
        if not 0.0 <= self.thermal_work_gain <= 1.0:
            raise ValueError("thermal_work_gain must be within [0, 1]")

        # Activity scaling and floors
        if not (0.0 <= self.activity_elevated_penalty <= 1.0):
            raise ValueError(f"activity_elevated_penalty must be within [0, 1]; got {self.activity_elevated_penalty}")
        if not (0.0 < self.activity_elevated_floor <= 1.0):
            raise ValueError(f"activity_elevated_floor must be within (0, 1]; got {self.activity_elevated_floor}")
        if not (0.0 <= self.activity_severe_penalty <= 1.0):
            raise ValueError(f"activity_severe_penalty must be within [0, 1]; got {self.activity_severe_penalty}")
        if not (0.0 < self.activity_severe_floor <= 1.0):
            raise ValueError(f"activity_severe_floor must be within (0, 1]; got {self.activity_severe_floor}")

        # Safe mode
        if not (0.0 <= self.safe_mode_integrity_threshold <= 1.0):
            raise ValueError(f"safe_mode_integrity_threshold must be within [0, 1]; got {self.safe_mode_integrity_threshold}")
        if not (0.0 < self.safe_mode_activity_scale <= 1.0):
            raise ValueError(f"safe_mode_activity_scale must be within (0, 1]; got {self.safe_mode_activity_scale}")

        # Dormant factor
        if not (0.0 < self.dormant_metabolic_factor <= 1.0):
            raise ValueError(f"dormant_metabolic_factor must be within (0, 1]; got {self.dormant_metabolic_factor}")

        # Aging and waste ticks
        if not isinstance(self.aging_ticks, int) or self.aging_ticks < 1:
            raise ValueError(f"aging_ticks must be an integer >= 1; got {self.aging_ticks}")
        if not isinstance(self.waste_ticks, int) or self.waste_ticks < 1:
            raise ValueError(f"waste_ticks must be an integer >= 1; got {self.waste_ticks}")


DEFAULT_PHYSIOLOGY_CONFIG = PhysiologyConfig()

__all__ = [
    "PhysiologyConfig",
    "DEFAULT_PHYSIOLOGY_CONFIG",
]
