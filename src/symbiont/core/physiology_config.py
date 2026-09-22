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
    growth_rate_per_tick: float = 0.01
    growth_energy_fraction_per_progress: float = 0.20
    senescence_start_ticks: int = 2048
    senescence_rate_per_tick: float = 0.001
    senescence_wear_rate: float = 0.0002
    reproduction_energy_fraction: float = 0.25
    reproduction_min_integrity: float = 0.80
    reproduction_max_senescence: float = 0.75

    # Prospective agency (L8) — constitutional cognitive capacity.
    # These parameters belong to the organism's innate deliberation kernel,
    # not to any task or environmental target.
    prospective_query_cost: float = 0.0005
    prospective_max_candidates: int = 8
    prospective_min_model_confidence: float = 0.5
    prospective_min_value_samples: int = 4
    prospective_decision_margin: float = 0.02

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
            "growth_rate_per_tick",
            "growth_energy_fraction_per_progress",
            "senescence_start_ticks",
            "senescence_rate_per_tick",
            "senescence_wear_rate",
            "reproduction_energy_fraction",
            "reproduction_min_integrity",
            "reproduction_max_senescence",
            "prospective_query_cost",
            "prospective_max_candidates",
            "prospective_min_model_confidence",
            "prospective_min_value_samples",
            "prospective_decision_margin",
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
            "growth_rate_per_tick",
            "growth_energy_fraction_per_progress",
            "senescence_rate_per_tick",
            "senescence_wear_rate",
            "reproduction_energy_fraction",
            "reproduction_min_integrity",
            "reproduction_max_senescence",
            "prospective_query_cost",
            "prospective_min_model_confidence",
            "prospective_decision_margin",
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

        # Ontogeny is constitutional physiology, never a cognitive achievement.
        if not 0.0 < self.growth_rate_per_tick <= 1.0:
            raise ValueError("growth_rate_per_tick must be within (0, 1]")
        if not 0.0 < self.growth_energy_fraction_per_progress <= 1.0:
            raise ValueError(
                "growth_energy_fraction_per_progress must be within (0, 1]"
            )
        if not isinstance(self.senescence_start_ticks, int) or self.senescence_start_ticks < 1:
            raise ValueError("senescence_start_ticks must be an integer >= 1")
        if not 0.0 <= self.senescence_rate_per_tick <= 1.0:
            raise ValueError("senescence_rate_per_tick must be within [0, 1]")
        if not 0.0 <= self.senescence_wear_rate <= 1.0:
            raise ValueError("senescence_wear_rate must be within [0, 1]")
        if not 0.0 < self.reproduction_energy_fraction < 1.0:
            raise ValueError("reproduction_energy_fraction must be within (0, 1)")
        if not 0.0 <= self.reproduction_min_integrity <= 1.0:
            raise ValueError("reproduction_min_integrity must be within [0, 1]")
        if not 0.0 <= self.reproduction_max_senescence <= 1.0:
            raise ValueError("reproduction_max_senescence must be within [0, 1]")

        # Prospective agency (L8) constitutional parameter validation
        if not 0.0 <= self.prospective_query_cost <= 0.1:
            raise ValueError("prospective_query_cost must be within [0, 0.1]")
        if (
            isinstance(self.prospective_max_candidates, bool)
            or not isinstance(self.prospective_max_candidates, int)
            or not 1 <= self.prospective_max_candidates <= 32
        ):
            raise ValueError("prospective_max_candidates must be an integer in [1, 32]")
        if not 0.0 <= self.prospective_min_model_confidence <= 1.0:
            raise ValueError("prospective_min_model_confidence must be within [0, 1]")
        if (
            isinstance(self.prospective_min_value_samples, bool)
            or not isinstance(self.prospective_min_value_samples, int)
            or not 1 <= self.prospective_min_value_samples <= 64
        ):
            raise ValueError("prospective_min_value_samples must be an integer in [1, 64]")
        if not 0.0 <= self.prospective_decision_margin <= 1.0:
            raise ValueError("prospective_decision_margin must be within [0, 1]")


DEFAULT_PHYSIOLOGY_CONFIG = PhysiologyConfig()

__all__ = [
    "PhysiologyConfig",
    "DEFAULT_PHYSIOLOGY_CONFIG",
]
