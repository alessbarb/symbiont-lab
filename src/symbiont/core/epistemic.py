"""Canonical epistemic and representational conventions for Symbiont.

Defines the shared conventions for how the organism discretizes, quantizes,
smoothes, and considers signals established or mature.

These are distinct from physical resource bounds (:class:`~symbiont.core.limits.OrganismLimits`)
and physiological dynamics (:class:`~symbiont.core.physiology.PhysiologyConfig`).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RecencyClass(IntEnum):
    """Categorical recency bins for sensor and component activity."""

    CURRENT = 0
    SHORT_IDLE = 1
    IDLE = 2
    LONG_IDLE = 3
    DORMANT = 4


@dataclass(slots=True, frozen=True)
class EpistemicConventions:
    """Canonical epistemic parameters and quantization classes."""

    # Established observation thresholds
    established_signal_min_samples: int = 5

    # Exponentially weighted moving average smoothing factor
    ewma_alpha: float = 0.06

    # Discrete state binning classes
    health_classes: int = 16
    confidence_classes: int = 16
    cost_classes: int = 16
    maturity_classes: int = 8
    activity_classes: int = 16

    # Recency progression thresholds (in idle ticks)
    recency_thresholds: tuple[int, ...] = (10, 40, 120, 400)

    # Epistemic support epochs required to enter each maturity class
    maturity_thresholds: tuple[int, ...] = (0, 1, 2, 4, 8, 16, 32, 64)

    # Representative idle ticks assigned to each recency class
    recency_representative_idle_ticks: tuple[tuple[RecencyClass, int], ...] = (
        (RecencyClass.CURRENT, 0),
        (RecencyClass.SHORT_IDLE, 10),
        (RecencyClass.IDLE, 40),
        (RecencyClass.LONG_IDLE, 120),
        (RecencyClass.DORMANT, 400),
    )

    def __post_init__(self) -> None:
        # Check no bool masquerading as int/float
        if isinstance(self.established_signal_min_samples, bool) or not isinstance(self.established_signal_min_samples, int):
            raise ValueError("established_signal_min_samples must be an integer, not bool")
        if self.established_signal_min_samples < 1:
            raise ValueError(f"established_signal_min_samples must be >= 1; got {self.established_signal_min_samples}")

        if isinstance(self.ewma_alpha, bool) or not isinstance(self.ewma_alpha, (int, float)):
            raise ValueError("ewma_alpha must be a float, not bool")
        if not (0.0 < float(self.ewma_alpha) <= 1.0):
            raise ValueError(f"ewma_alpha must be in (0, 1]; got {self.ewma_alpha}")

        for class_name in ("health_classes", "confidence_classes", "cost_classes", "maturity_classes", "activity_classes"):
            val = getattr(self, class_name)
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"{class_name} must be an integer, not bool")
            if val <= 0:
                raise ValueError(f"{class_name} must be positive; got {val}")

        for t in self.recency_thresholds:
            if isinstance(t, bool) or not isinstance(t, int) or t < 0:
                raise ValueError(f"recency_thresholds elements must be non-negative integers; got {t}")
        for i in range(len(self.recency_thresholds) - 1):
            if self.recency_thresholds[i] >= self.recency_thresholds[i + 1]:
                raise ValueError(
                    f"recency_thresholds must be strictly increasing; got {self.recency_thresholds}"
                )

        for t in self.maturity_thresholds:
            if isinstance(t, bool) or not isinstance(t, int) or t < 0:
                raise ValueError(f"maturity_thresholds elements must be non-negative integers; got {t}")
        for i in range(len(self.maturity_thresholds) - 1):
            if self.maturity_thresholds[i] > self.maturity_thresholds[i + 1]:
                raise ValueError(
                    f"maturity_thresholds must be non-decreasing; got {self.maturity_thresholds}"
                )
        if len(self.maturity_thresholds) != self.maturity_classes:
            raise ValueError(
                f"maturity_thresholds count ({len(self.maturity_thresholds)}) "
                f"must equal maturity_classes ({self.maturity_classes})"
            )

        seen_classes: set[RecencyClass] = set()
        for pair in self.recency_representative_idle_ticks:
            if not (isinstance(pair, (tuple, list)) and len(pair) == 2):
                raise ValueError("recency_representative_idle_ticks must contain (RecencyClass, int) pairs")
            rc, ticks = pair
            if not isinstance(rc, RecencyClass):
                raise ValueError(f"expected RecencyClass in representative map; got {type(rc)}")
            if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 0:
                raise ValueError(f"representative ticks must be non-negative int; got {ticks}")
            seen_classes.add(rc)
        if seen_classes != set(RecencyClass):
            raise ValueError(f"recency_representative_idle_ticks must cover all RecencyClass variants; missing {set(RecencyClass) - seen_classes}")

    def recency_representative_map(self) -> dict[RecencyClass, int]:
        return dict(self.recency_representative_idle_ticks)

    def classify_recency(self, idle_ticks: int) -> RecencyClass:
        """Map idle tick count to a discrete RecencyClass."""
        if idle_ticks < self.recency_thresholds[0]:
            return RecencyClass.CURRENT
        if idle_ticks < self.recency_thresholds[1]:
            return RecencyClass.SHORT_IDLE
        if idle_ticks < self.recency_thresholds[2]:
            return RecencyClass.IDLE
        if idle_ticks < self.recency_thresholds[3]:
            return RecencyClass.LONG_IDLE
        return RecencyClass.DORMANT


# Default singleton instance for general organism use
DEFAULT_EPISTEMIC_CONVENTIONS = EpistemicConventions()

__all__ = [
    "RecencyClass",
    "EpistemicConventions",
    "DEFAULT_EPISTEMIC_CONVENTIONS",
]
