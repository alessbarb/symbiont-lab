from __future__ import annotations

from lab.physics3d.telemetry.tools import (
    evaluate_acceptance_gates,
)


def _state(tick: int):
    return {
        "schema_version": 3,
        "tick": tick,
        "pre": {"physical": {"x": tick * 0.1}},
        "runtime": {
            "knowledge_events": [],
            "runtime_events": [],
            "experience_records_created": [],
            "signal_knowledge": [],
            "sensory_phenotype": {},
        },
        "cognition": {"mutations": [], "recycling_events": []},
        "sensorimotor": {"episodes": []},
        "observer_semantics": {"provenance": {"feeds_back": False}},
        "future_unknown": tick,
    }


def test_acceptance_gate_reports_each_failed_constraint():
    report = {
        "version": "v4.1",
        "ticks": 3,
        "evidence_bytes_excluding_checkpoints": 500,
        "fallback_fraction": 0.25,
        "integrity": {"complete": False},
        "state_at_ms": {"p95": 250.0},
    }

    gate = evaluate_acceptance_gates(
        report,
        expected_ticks=4,
        max_evidence_bytes=100,
        max_fallback_fraction=0.05,
        max_state_at_p95_ms=100.0,
    )

    assert gate["passed"] is False
    assert gate["checks"] == {
        "version_is_v41": True,
        "integrity_complete": False,
        "evidence_bytes": False,
        "fallback_fraction": False,
        "state_at_p95_ms": False,
        "expected_ticks": False,
    }
