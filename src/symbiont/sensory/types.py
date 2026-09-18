"""Boundary type aliases for the adaptive sensory architecture.

Raw host acquisition keeps the historical SensorReading class during the
migration window.  The alias is explicit so new code can use the correct
conceptual name without breaking historical callers.
"""
from __future__ import annotations

from ..host.readings import SensorReading as RawSample
from ..host.percepts import Percept

__all__ = ["RawSample", "Percept"]
