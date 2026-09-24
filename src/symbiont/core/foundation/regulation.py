"""Canonical metaplastic regulation surface.

The former independent PhenotypicRegulationState implementation has been
removed. All lifetime genetic regulation now flows through
symbiont.genetics.expression.
"""
from symbiont.genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)

# Transitional import name only; it is the same state object, not another
# regulator or another expression representation.
PhenotypicRegulationState = GeneExpressionState

__all__ = [
    "ExpressionRegulator",
    "GeneExpressionState",
    "PhenotypicRegulationState",
    "RegulatorySignals",
]
