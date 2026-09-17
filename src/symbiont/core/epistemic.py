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
