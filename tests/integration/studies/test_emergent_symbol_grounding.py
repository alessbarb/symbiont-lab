from __future__ import annotations

import ast
from pathlib import Path

from symbiont_lab.studies.learning.emergent_symbol_grounding import (
    run_emergent_symbol_grounding_study,
)

SOURCE = Path("src/symbiont_lab/studies/learning/emergent_symbol_grounding.py")


def test_preregistered_symbol_study_passes_all_current_baseline_gates() -> None:
    result = run_emergent_symbol_grounding_study()
    assert result.seeds == (101, 127, 149)
    assert result.all_gates_pass is True
    assert result.replay_deterministic is True
    assert all(item.prediction_gain > item.no_signal_gain for item in result.per_seed)
    assert all(item.prediction_gain > item.random_signal_gain for item in result.per_seed)


def test_autonomous_path_has_no_evaluator_symbol_selector_or_meaning_table() -> None:
    tree = ast.parse(SOURCE.read_text())
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "choose_symbol" not in calls
    source = SOURCE.read_text()
    assert "SYMBOL_MEANINGS" not in source
    assert "canonical_symbol_for" not in source
    # The only direct SymbolMessage construction is in explicit random/permutation controls.
    autonomous = source[
        source.index("else:\n            decision = emitter.autonomous_symbol_step") :
    ]
    assert (
        "SymbolMessage"
        not in autonomous.split("for tick in range(training_ticks + evaluation_ticks):", 1)[0]
    )
