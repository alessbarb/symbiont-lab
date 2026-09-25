"""Constitutional, semantic-free regulation below deliberative agency."""

from symbiont.core.foundation.regulation import GeneExpressionState

from .arbitration import ActionArbitrator, ArbitrationDecision
from .reactive_memory import ReactiveAssociation, ReactiveMemory
from .reactivity import InnateReactivity
from .types import ReactiveState

# Compatibility name for historical regulation tests and checkpoints.  The
# canonical implementation remains the shared gene-expression state.
PhenotypicRegulationState = GeneExpressionState

__all__ = [
    "ActionArbitrator",
    "ArbitrationDecision",
    "InnateReactivity",
    "ReactiveAssociation",
    "ReactiveMemory",
    "ReactiveState",
    "PhenotypicRegulationState",
]
