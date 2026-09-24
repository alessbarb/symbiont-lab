"""Compatibility result for pre-v2 reactive memory callers.

This type exists only so old checkpoints/tests can be read while ActionArbitrator
itself is the universal v2 arbitrator.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegacyArbitrationDecision:
    primitive_id: str | None
    reason: str
