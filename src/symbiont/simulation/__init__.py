"""Legacy Agent population simulation: engine, evaluation, metrics, snapshots.

Status: legacy-supported apparatus. This stack predates the canonical
``OrganismRuntime``. Its ``Agent`` assesses externally labelled host
observations (CPU, network, file changes, threat, risk, curiosity) and is not
the modern organism: it shares no state, checkpoint or cognition with it, and
nothing it produces enters an ``OrganismRuntime``. It remains executable only
because recorded studies and their protocols run on it. See
``docs/design/core/legacy-agent-simulation-status-v1.md``.
"""

from .engine import (
    ARCHITECTURE,
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
    "ARCHITECTURE",
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
