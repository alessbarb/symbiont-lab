from __future__ import annotations

from symbiont.cognition.types import (
    EDGE_DELAY_TICKS_RANGE,
    GATE_RANGE,
    PLASTICITY_RANGE,
    TAU_RANGE,
    WEIGHT_RANGE,
    EdgeKind,
    NodeKind,
)


def test_node_kind_catalog_is_exactly_the_documented_six():
    assert {kind.value for kind in NodeKind} == {
        "sense",
        "concept",
        "state",
        "predictor",
        "gate",
        "readout",
    }


def test_no_action_node_kind_exists():
    assert not any(kind.value == "action" for kind in NodeKind)


def test_edge_kind_catalog_is_exactly_the_documented_four():
    assert {kind.value for kind in EdgeKind} == {"excitatory", "inhibitory", "predictive", "gating"}


def test_ranges_match_the_design_doc():
    assert WEIGHT_RANGE == (-2.0, 2.0)
    assert PLASTICITY_RANGE == (0.0, 1.0)
    assert GATE_RANGE == (0.0, 1.0)
    assert EDGE_DELAY_TICKS_RANGE == (0, 1)
    assert TAU_RANGE == (0.1, 10.0)
