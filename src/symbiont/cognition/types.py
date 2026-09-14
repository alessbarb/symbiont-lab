from __future__ import annotations

from enum import StrEnum


class NodeKind(StrEnum):
    """Closed catalog (roadmap v0.55, master doc §5.1). There is
    deliberately no ACTION kind -- readouts feed existing, already-governed
    consultative circuits; the graph itself never acts."""

    SENSE = "sense"
    CONCEPT = "concept"
    STATE = "state"
    PREDICTOR = "predictor"
    GATE = "gate"
    READOUT = "readout"


class EdgeKind(StrEnum):
    """Closed catalog (master doc §5.2)."""

    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"
    PREDICTIVE = "predictive"
    GATING = "gating"


WEIGHT_RANGE: tuple[float, float] = (-2.0, 2.0)
PLASTICITY_RANGE: tuple[float, float] = (0.0, 1.0)
GATE_RANGE: tuple[float, float] = (0.0, 1.0)
EDGE_DELAY_TICKS_RANGE: tuple[int, int] = (0, 1)
