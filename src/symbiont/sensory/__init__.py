"""Organism-owned sensory transduction layer.

The host discovers observable sources; this package owns how an individual
Symbiont turns those sources into percepts.  Keeping the boundary explicit
prevents provider/platform semantics from becoming cognitive semantics.
"""

from .limits import SensoryLimits
from .modalities import DEFAULT_MODALITIES, SensoryModality
from .selection import PairwisePredictiveEvidence, SensorySelectionEngine
from .sensor import MaturityState, SensorState
from .system import SensorySystem
from .transduction import TransductionKind

__all__ = [
    "DEFAULT_MODALITIES",
    "MaturityState",
    "SensoryLimits",
    "SensoryModality",
    "SensorySelectionEngine",
    "PairwisePredictiveEvidence",
    "SensorySystem",
    "SensorState",
    "TransductionKind",
]
