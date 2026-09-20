from __future__ import annotations

import ast
from pathlib import Path

import pytest

from symbiont.core.germline import (
    EpigeneticMark,
    SymbiontGenome,
    create_germline_state,
    create_standard_genome,
)
from symbiont.core.regulation import PhenotypicRegulationState
from symbiont.core.symbiont import Symbiont


def _genome(genome_id: str, **overrides: float | int) -> SymbiontGenome:
    base = create_standard_genome(genome_id)
    return SymbiontGenome(
        genome_id=genome_id,
        loci_values={**dict(base.loci_values), **overrides},
        specs=base.specs,
    )


def test_m1_regulator_is_semantically_invariant_to_external_names():
    genome = _genome("m1")
    birth = {
        "learning_rate": float(genome.get("learning_rate")),
        "exploration_rate": float(genome.get("exploration_rate")),
    }
    a = PhenotypicRegulationState(birth_expression=dict(birth), specs=genome.specs)
    b = PhenotypicRegulationState(birth_expression=dict(birth), specs=genome.specs)

    # The regulator receives no names at all; identical internal trajectories
    # must therefore be exactly identical regardless of apparatus labels.
    trajectory = [(0.0, False), (0.5, False), (0.8, True), (0.2, False)] * 40
    for error, disruption in trajectory:
        state_a, eligible_a = a.update(prediction_error=error, disruption=disruption)
        state_b, eligible_b = b.update(prediction_error=error, disruption=disruption)
        assert state_a == state_b
        assert eligible_a == eligible_b


def test_m2_transient_shock_does_not_create_acquired_mark():
    genome = _genome("m2")
    germline = create_germline_state(genome)
    sym = Symbiont("m2-sym", genome=genome, germline=germline)

    regulator = sym.phenotypic_regulator
    assert regulator is not None

    # Drive regulator directly with an internal error shock shorter than the
    # preregistered 64-tick persistence window.
    for _ in range(regulator.persistence_ticks_required - 1):
        current, eligible = regulator.update(prediction_error=1.0, disruption=True)
        assert "learning_rate" not in eligible

    assert germline.acquired_marks == {}


def test_m3_sustained_prediction_pressure_becomes_capture_eligible():
    genome = _genome("m3", learning_rate=0.10, exploration_rate=0.20)
    germline = create_germline_state(genome)
    regulator = PhenotypicRegulationState(
        birth_expression={
            "learning_rate": germline.birth_expression["learning_rate"],
            "exploration_rate": germline.birth_expression["exploration_rate"],
        },
        specs=genome.specs,
    )

    eligible: tuple[str, ...] = ()
    current = {}
    for _ in range(160):
        current, eligible = regulator.update(prediction_error=1.0, disruption=True)

    assert eligible
    captured = germline.capture_acquired_variation(
        {locus: current[locus] for locus in eligible},
        specs=genome.specs,
        min_delta=regulator.min_capture_delta,
        max_marks=int(genome.get("max_epigenetic_marks")),
    )
    assert captured
    assert set(captured) <= {"learning_rate", "exploration_rate"}
    assert set(germline.acquired_marks) == set(captured)


def test_m4_expression_relaxes_toward_birth_after_pressure_ends():
    genome = _genome("m4")
    germline = create_germline_state(genome)
    regulator = PhenotypicRegulationState(
        birth_expression={
            "learning_rate": germline.birth_expression["learning_rate"],
            "exploration_rate": germline.birth_expression["exploration_rate"],
        },
        specs=genome.specs,
    )

    for _ in range(120):
        regulator.update(prediction_error=1.0, disruption=True)

    elevated = dict(regulator.current_expression)
    for _ in range(240):
        regulator.update(prediction_error=0.0, disruption=False)
    relaxed = dict(regulator.current_expression)

    for locus in ("learning_rate", "exploration_rate"):
        birth = regulator.birth_expression[locus]
        assert abs(relaxed[locus] - birth) < abs(elevated[locus] - birth)


def test_m5_inherited_mark_is_birth_expression_not_new_acquisition():
    genome = _genome("m5", learning_rate=0.10)
    inherited = EpigeneticMark(
        locus="learning_rate",
        delta=0.10,
        strength=0.8,
        generations_left=2,
    )
    germline = create_germline_state(genome, epigenetic_marks=(inherited,))

    assert germline.inherited_marks["learning_rate"] == inherited
    assert germline.acquired_marks == {}
    assert germline.birth_expression["learning_rate"] == pytest.approx(0.18)

    sym = Symbiont("m5-sym", genome=genome, germline=germline)
    assert sym.learning_rate == pytest.approx(0.18)

    # Neutral internal dynamics do not convert the inherited difference from
    # raw genome into a newly acquired mark.
    regulator = sym.phenotypic_regulator
    assert regulator is not None
    for _ in range(200):
        regulator.update(prediction_error=0.0, disruption=False)

    assert germline.acquired_marks == {}


def test_m6_regulator_has_no_world_lab_reward_or_fitness_dependency():
    source = Path("src/symbiont/core/regulation.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_modules = ("symbiont_lab", "symbiont_world")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith(forbidden_modules) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith(forbidden_modules)

    lowered = source.lower()
    for token in (
        "fitness",
        "reward",
        "resource_id",
        "hazard_id",
        "survival_score",
        "offspring_count",
    ):
        assert token not in lowered
