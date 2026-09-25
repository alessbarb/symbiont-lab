from __future__ import annotations

import ast
from pathlib import Path

from symbiont_lab.studies.learning.independent_symbol_grounding import (
    run_independent_symbol_grounding_study,
)

SOURCE = Path("src/symbiont_lab/studies/learning/independent_symbol_grounding.py")


def test_preregistered_study_reports_the_committed_seeds_and_static_checks() -> None:
    result = run_independent_symbol_grounding_study()
    assert result.seeds == (101, 127, 149)
    assert result.isg5_no_shared_seed_leakage is True
    assert result.isg6_no_evaluator_symbol_selection is True
    assert result.replay_deterministic is True


def test_isolated_and_shuffled_twins_stay_at_chance_on_every_seed() -> None:
    """H0 twins must never spuriously reject the chance null; if they do, the
    metric or mechanism is broken, not evidence for emergence."""
    result = run_independent_symbol_grounding_study()
    for item in result.per_seed:
        assert item.isg2_isolated_at_chance is True
        assert item.isg3_shuffled_at_chance is True


def test_preregistered_result_is_the_honestly_reported_negative_finding() -> None:
    """First preregistered run (see experiment.toml [result]): isg1/isg4 FAILED
    on every seed under this mechanism -- no significant interactive
    convergence over chance was observed. This is evidence FOR H0 on symbol
    grounding and must not be silently papered over by loosening the gates."""
    result = run_independent_symbol_grounding_study()
    for item in result.per_seed:
        assert item.isg1_interactive_convergence is False
        assert item.isg4_delta_not_baseline_artifact is False
    assert result.all_gates_pass is False


def test_no_shared_symbol_policy_seed_between_emitters() -> None:
    source = SOURCE.read_text()
    tree = ast.parse(source)
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "choose_symbol" not in calls
    # emitter_b must always derive its seed via _independent_seed, never reuse `seed` directly.
    assert "seed_b = _independent_seed(seed)" in source
    assert "symbol_policy_seed=seed_b" in source
    emitter_b_line = next(
        line for line in source.splitlines() if "emitter_b = ModeledOrganismRuntime" in line
    )
    assert "symbol_policy_seed=seed_b" in emitter_b_line
