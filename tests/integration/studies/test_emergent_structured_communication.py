from __future__ import annotations

import ast
from pathlib import Path

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.emergent_structured_communication import (
    run_emergent_structured_communication_study,
)


SOURCE = Path("src/symbiont_lab/studies/learning/emergent_structured_communication.py")


def test_structured_communication_study_is_registered_and_replayable() -> None:
    assert get_protocol("learning.emergent-structured-communication").__name__ == "run_emergent_structured_communication_study"
    result = run_emergent_structured_communication_study()
    assert result.seeds == (101, 127, 149)
    assert result.conditions == ("no_signal", "random_signal", "autonomous")
    assert result.all_gates_pass is True
    assert all(item.replay_deterministic for item in result.per_seed)
    assert all(item.messages_sent > 0 and item.silence_count > 0 for item in result.per_seed)


def test_active_study_has_no_prescriptive_message_planner() -> None:
    tree = ast.parse(SOURCE.read_text())
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    source = SOURCE.read_text()
    assert "ground_truth" not in names
    assert "SYMBOL_MEANINGS" not in source
    assert "canonical_symbol_for" not in source
    assert "target_sequence" not in source
    assert "factor_A" not in source
    assert "factor_B" not in source


def test_productivity_is_descriptive_not_a_closure_requirement() -> None:
    result = run_emergent_structured_communication_study(seeds=(101,))
    assert result.esc5_structure_analysis_available is True
    assert result.esc6_productive_generalization is False
