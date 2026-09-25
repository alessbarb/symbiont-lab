"""Canonical operational runtime defaults for Symbiont organisms.

These define default filesystem locations, check cadence and timing
for transparent user-service and foreground resident runs.
They are distinct from organism biological limits and internal epistemic conventions.
"""

from __future__ import annotations

DEFAULT_STATE_FILE: str = "~/.local/state/symbiont/organism.json"
DEFAULT_TICK_INTERVAL_SECONDS: float = 15.0
DEFAULT_CHECKPOINT_TICKS: int = 20

__all__ = [
    "DEFAULT_STATE_FILE",
    "DEFAULT_TICK_INTERVAL_SECONDS",
    "DEFAULT_CHECKPOINT_TICKS",
]
