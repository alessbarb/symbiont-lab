"""Unit tests for motor_competence_candidates() builder."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.actuation.competence import CompetenceMaturity
from symbiont.agency.candidates import _MAX_CANDIDATES, motor_competence_candidates
from symbiont.agency.types import ProspectiveCandidate


# NOTE(stub): Minimal controller stub — only its identity and maturity cross the boundary.
@dataclass
class _FakeController:
    primitive_id: str
    maturity: CompetenceMaturity = CompetenceMaturity.ESTABLISHED


def _prims(*ids, competent=True):
    maturity = (
        CompetenceMaturity.ESTABLISHED
        if competent
        else CompetenceMaturity.CANDIDATE
    )
    return [_FakeController(primitive_id=pid, maturity=maturity) for pid in ids]


def test_empty_primitives_returns_empty():
    result = motor_competence_candidates([], {})
    assert result == ()


def test_only_competent_primitives_included():
    prims = _prims("p.a", "p.b") + [_FakeController("p.c", CompetenceMaturity.CANDIDATE)]
    readouts = {"p.a": 0.2, "p.b": 0.3, "p.c": 0.9}
    result = motor_competence_candidates(prims, readouts)
    ids = {c.action_id for c in result}
    assert "p.a" in ids
    assert "p.b" in ids
    assert "p.c" not in ids


def test_high_readout_does_not_hide_cognitively_admitted_primitive():
    prims = _prims("p.high", "p.low")
    readouts = {"p.high": 0.9, "p.low": 0.1}
    result = motor_competence_candidates(prims, readouts)
    ids = {candidate.action_id for candidate in result}
    assert ids == {"p.high", "p.low"}


def test_no_readout_excludes_primitive():
    prims = _prims("p.a", "p.b")
    readouts = {"p.a": 0.3}  # p.b has no readout
    result = motor_competence_candidates(prims, readouts)
    ids = {c.action_id for c in result}
    assert "p.a" in ids
    assert "p.b" not in ids


def test_order_is_deterministic_by_primitive_id():
    prims = _prims("p.z", "p.a", "p.m")
    readouts = {"p.z": 0.1, "p.a": 0.2, "p.m": 0.3}
    result = motor_competence_candidates(prims, readouts)
    ids = [c.action_id for c in result]
    assert ids == sorted(ids), "candidates must be sorted by primitive_id"


def test_max_candidates_enforced():
    prims = _prims(*[f"p.{i:03d}" for i in range(20)])
    readouts = {p.primitive_id: 0.1 for p in prims}
    result = motor_competence_candidates(prims, readouts)
    assert len(result) <= _MAX_CANDIDATES


def test_custom_max_candidates_capped_at_8():
    prims = _prims(*[f"p.{i:03d}" for i in range(20)])
    readouts = {p.primitive_id: 0.1 for p in prims}
    result = motor_competence_candidates(prims, readouts, max_candidates=999)
    assert len(result) <= _MAX_CANDIDATES


def test_all_candidates_have_primitive_family():
    prims = _prims("p.a", "p.b", "p.c")
    readouts = {"p.a": 0.1, "p.b": 0.2, "p.c": 0.3}
    result = motor_competence_candidates(prims, readouts)
    assert all(c.family == "competence" for c in result)


def test_returns_prospective_candidate_instances():
    prims = _prims("p.x")
    readouts = {"p.x": 0.2}
    result = motor_competence_candidates(prims, readouts)
    assert len(result) == 1
    assert isinstance(result[0], ProspectiveCandidate)
    assert result[0].action_id == "p.x"


def test_zero_readout_included():
    """A competence with readout 0.0 is not 'active' and should be included."""
    prims = _prims("p.zero")
    readouts = {"p.zero": 0.0}
    result = motor_competence_candidates(prims, readouts)
    assert len(result) == 1


def test_readout_at_threshold_boundary():
    """Readout exactly at 0.5 threshold should be included (>threshold)."""
    prims = _prims("p.exact")
    readouts = {"p.exact": 0.5}
    # threshold is 0.5, condition is `readout > 0.5`, so 0.5 is included
    result = motor_competence_candidates(prims, readouts)
    assert len(result) == 1
