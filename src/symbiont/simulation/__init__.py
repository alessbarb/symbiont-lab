"""Symbiont simulation engine, evaluation, metrics, and snapshots."""

from .engine import (
    SimulationConfig,
    _cognitive_outputs,
    _make_agents,
    _rate_or_zero,
    _run_population,
    _snapshot,
    _trust_gap,
    run_simulation,
)
from .evaluation import CalibrationBin, EvaluationCounts, Evaluator
from .events import EventContext
from .metrics import brier_score, expected_calibration_error, rate
from .result import SimulationResult
from .snapshots import SimulationSnapshot

__all__ = [
    "CalibrationBin",
    "EvaluationCounts",
    "Evaluator",
    "EventContext",
    "SimulationConfig",
    "SimulationResult",
    "SimulationSnapshot",
    "_cognitive_outputs",
    "_make_agents",
    "_rate_or_zero",
    "_run_population",
    "_snapshot",
    "_trust_gap",
    "brier_score",
    "expected_calibration_error",
    "rate",
    "run_simulation",
]
