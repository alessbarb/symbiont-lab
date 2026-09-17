from __future__ import annotations

import ast
from pathlib import Path

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.structured_communication_characterization import run_structured_communication_characterization


SOURCE = Path("src/symbiont_lab/studies/learning/structured_communication_characterization.py")


def test_characterization_is_registered_and_replayable():
    result = run_structured_communication_characterization(seeds=(101,))
    assert get_protocol("learning.structured-communication-characterization") is run_structured_communication_characterization
    assert len(result.per_seed) == 9
    assert all(item.replay_deterministic for item in result.per_seed)
    assert result.holdout_isolated and result.evaluator_only_metrics


def test_characterization_has_controls_and_variable_pressure_without_linguistic_targets():
    result = run_structured_communication_characterization(seeds=(101,))
    assert {item.condition for item in result.per_seed} >= {"no_signal", "random_signal", "sequence_disabled", "full_channel"}
    assert {item.max_message_length for item in result.per_seed} >= {1, 4}
    source = SOURCE.read_text()
    names = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    assert "ground_truth" not in names
    for forbidden in ("factor_A", "factor_B", "semantic_slot", "target_message", "canonical_symbol_for"):
        assert forbidden not in source
