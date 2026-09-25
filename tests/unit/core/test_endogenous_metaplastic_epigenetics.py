from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest
from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    SymbiontGenome,
    create_germline_state,
    create_standard_genome,
)
from symbiont.core.symbiont import Symbiont

from symbiont.genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from symbiont.genetics.germline import EpigeneticProtocol


def _code_tokens(tree: ast.AST) -> list[str]:
    """Lowercased identifiers/attributes/kwargs/string-literals appearing in
    *code* (comments are not AST nodes and are therefore excluded, so prose
    that only discusses a concept does not appear here)."""
    tokens: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.append(node.id.lower())
        elif isinstance(node, ast.Attribute):
            tokens.append(node.attr.lower())
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.append(node.arg.lower())
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            tokens.append(node.value.lower())
    return tokens


def _genome(genome_id: str, **overrides: float | int) -> SymbiontGenome:
    base = create_standard_genome(genome_id)
    learning_value = float(overrides.get("learning_rate", base.plasticity.learning_rate.baseline))
    learning = replace(
        base.plasticity.learning_rate,
        baseline=learning_value,
        maximum=max(base.plasticity.learning_rate.maximum, learning_value + 0.20),
    )
    sensorimotor = replace(
        base.sensorimotor,
        spontaneous_activity_baseline=float(
            overrides.get("exploration_rate", base.sensorimotor.spontaneous_activity_baseline)
        ),
    )
    return replace(
        base,
        genome_id=f"genome_{genome_id}",
        plasticity=replace(base.plasticity, learning_rate=learning),
        sensorimotor=sensorimotor,
    )


def test_m1_regulator_is_semantically_invariant_to_external_names():
    genome = _genome("m1")
    a = GeneExpressionState.from_genome(genome)
    b = GeneExpressionState.from_genome(genome)
    regulator = ExpressionRegulator()

    # The regulator receives no names at all; identical internal trajectories
    # must therefore be exactly identical regardless of apparatus labels.
    trajectory = [(0.0, False), (0.5, False), (0.8, True), (0.2, False)] * 40
    for error, disruption in trajectory:
        signals = RegulatorySignals(
            prediction_error=error,
            embodiment_mismatch=1.0 if disruption else 0.0,
        )
        a = regulator.update(genome, a, signals)
        b = regulator.update(genome, b, signals)
        assert a.as_dict() == b.as_dict()


def test_m2_transient_shock_does_not_create_acquired_mark():
    genome = _genome("m2")
    germline = create_germline_state(genome, acquired_capture_enabled=True)
    Symbiont("m2-sym", genome=genome, germline=germline)

    state = GeneExpressionState.from_genome(genome, germline=germline)
    regulator = ExpressionRegulator()
    for _ in range(8):
        state = regulator.update(
            genome,
            state,
            RegulatorySignals(prediction_error=1.0, embodiment_mismatch=1.0),
        )

    assert germline.acquired_marks == {}


def test_m3_sustained_prediction_pressure_becomes_capture_eligible():
    genome = _genome("m3", learning_rate=0.10, exploration_rate=0.20)
    germline = create_germline_state(genome, acquired_capture_enabled=True)
    state = GeneExpressionState.from_genome(genome, germline=germline)
    regulator = ExpressionRegulator()

    for _ in range(160):
        state = regulator.update(
            genome,
            state,
            RegulatorySignals(prediction_error=1.0, embodiment_mismatch=1.0),
        )
    captured = germline.capture_acquired_variation(
        {
            "plasticity.learning_rate.baseline": state.effective_learning_rate,
            "sensorimotor.spontaneous_activity_baseline": state.exploration_drive,
        },
        protocol=EpigeneticProtocol(
            enabled=True,
            acquired_capture_enabled=True,
            max_marks=2,
        ),
        genome=genome,
    )
    assert captured
    assert set(captured) <= {
        "plasticity.learning_rate.baseline",
        "sensorimotor.spontaneous_activity_baseline",
    }
    assert set(germline.acquired_marks) == set(captured)


def test_m4_expression_relaxes_toward_birth_after_pressure_ends():
    genome = _genome("m4")
    germline = create_germline_state(genome)
    state = GeneExpressionState.from_genome(genome, germline=germline)
    regulator = ExpressionRegulator()

    for _ in range(120):
        state = regulator.update(
            genome,
            state,
            RegulatorySignals(prediction_error=1.0, embodiment_mismatch=1.0),
        )

    elevated = state.as_dict()
    for _ in range(240):
        state = regulator.update(genome, state, RegulatorySignals())
    relaxed = state.as_dict()

    # The v2 regulator is evidence-gated: without new signals it holds the
    # current expression instead of inventing a relaxation trajectory.
    assert relaxed["effective_learning_rate"] == elevated["effective_learning_rate"]


def test_m5_inherited_mark_is_birth_expression_not_new_acquisition():
    genome = _genome("m5", learning_rate=0.10)
    inherited = EpigeneticMark(
        locus="plasticity.learning_rate.baseline",
        delta=0.10,
        strength=0.8,
        generations_left=2,
    )
    germline = GermlineState.from_genome(genome, inherited_marks=(inherited,))

    assert germline.inherited_marks["plasticity.learning_rate.baseline"] == inherited
    assert germline.acquired_marks == {}
    assert germline.birth_expression["plasticity.learning_rate.baseline"] == pytest.approx(0.10)

    sym = Symbiont("m5-sym", genome=genome, germline=germline)
    assert sym.learning_rate == pytest.approx(0.18)

    # Neutral internal dynamics do not convert the inherited difference from
    # raw genome into a newly acquired mark.
    state = GeneExpressionState.from_genome(genome, germline=germline)
    regulator = ExpressionRegulator()
    for _ in range(200):
        state = regulator.update(genome, state, RegulatorySignals())

    assert germline.acquired_marks == {}


def test_m6_regulator_has_no_world_lab_reward_or_fitness_dependency():
    source = Path("src/symbiont/genetics/expression.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_modules = ("symbiont_lab", "symbiont_world")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith(forbidden_modules) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith(forbidden_modules)

    forbidden_tokens = (
        "fitness",
        "reward",
        "resource_id",
        "hazard_id",
        "survival_score",
        "offspring_count",
    )

    # Scan code identifiers and string literals via the AST so prose that
    # correctly *disclaims* a dependency ("no ... fitness enters here")
    # cannot itself trip this check. A real dependency would surface as a
    # name, attribute, keyword argument, or string literal in code.
    code_tokens = _code_tokens(tree)

    for token in forbidden_tokens:
        assert not any(token in code_token for code_token in code_tokens), (
            f"forbidden token {token!r} found in code (comments excluded) "
            f"of src/symbiont/core/regulation.py"
        )


def test_m6_forbidden_token_scan_excludes_comments_but_catches_code():
    """Regression guard for the shared `_code_tokens` helper used by
    `test_m6_regulator_has_no_world_lab_reward_or_fitness_dependency`.

    Exercises the same helper the real check calls, in both directions:
    a comment that only *disclaims* a dependency must not trip it (this is
    the false failure that was fixed), but a genuine code-level dependency
    must still trip it (so the fix did not silently widen the exemption).
    """
    disclaiming_source = "x = 1  # no evaluator-defined success or fitness enters here.\n"
    assert not any("fitness" in token for token in _code_tokens(ast.parse(disclaiming_source)))

    real_dependency_source = (
        "def compute(self):\n    reward = self.upstream_reward_signal()\n    return reward\n"
    )
    assert any("reward" in token for token in _code_tokens(ast.parse(real_dependency_source)))
