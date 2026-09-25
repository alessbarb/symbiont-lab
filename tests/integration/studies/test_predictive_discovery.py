from __future__ import annotations

import ast
from pathlib import Path

import pytest

from symbiont_lab.evaluation.holdout import SeedLedger
from symbiont_lab.studies.learning.predictive_discovery import run_predictive_discovery_study

SOURCE = Path("src/symbiont_lab/studies/learning/predictive_discovery.py")


def test_preregistered_discovery_study_passes_all_gates(tmp_path) -> None:
    result = run_predictive_discovery_study(ledger=SeedLedger(tmp_path / "ledger.json"))
    assert result.development_seeds == (11, 23, 37)
    assert result.evaluation_seeds == (211, 233, 257)
    assert result.all_gates_pass is True
    assert result.pd1_correct_source_promoted is True
    assert result.pd2_no_decoy_promoted is True
    assert result.pd3_holdout_loss_gain is True
    assert result.pd4_decoy_control_fails_margin is True
    assert result.pd5_no_precabled_structure is True
    assert result.pd6_learned_predictor_input is True
    assert result.replay_deterministic is True
    for item in result.per_seed:
        assert item.promoted_source_id == "s_true"
        assert item.evaluation_source_gain > 0.0
        assert item.evaluation_best_decoy_gain < item.evaluation_source_gain
        assert item.pd6_learned_predictor_input is True


def test_evaluation_seeds_are_disjoint_from_development_seeds(tmp_path) -> None:
    result = run_predictive_discovery_study(ledger=SeedLedger(tmp_path / "ledger.json"))
    assert not set(result.development_seeds) & set(result.evaluation_seeds)


def test_reusing_a_development_seed_as_an_evaluation_seed_is_rejected(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    run_predictive_discovery_study(
        development_seeds=(11, 23, 37),
        evaluation_seeds=(211, 233, 257),
        ledger=ledger,
    )
    with pytest.raises(ValueError, match="overlap"):
        run_predictive_discovery_study(
            development_seeds=(999,),
            evaluation_seeds=(11,),
            ledger=ledger,
        )


def test_no_precabled_predictor_or_edge_in_source() -> None:
    source = SOURCE.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "predicts_node_id":
            raise AssertionError("predicts_node_id must never be constructed at graph-build time")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "PlasticEdge"
        ):
            raise AssertionError("no PlasticEdge may be constructed in this module")
    assert "kind=NodeKind.PREDICTOR" not in source
