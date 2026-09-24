"""Sensorimotor v2 arbitration compatibility boundary.

The universal ActionArbitrator lives with the action system.  Regulation keeps
this import path for existing callers, but no longer owns a second motor
arbiter.
"""
from ...actuation.arbitration import ActionArbitrator
from .arbitration_legacy import LegacyArbitrationDecision as ArbitrationDecision

__all__ = ["ActionArbitrator", "ArbitrationDecision"]
