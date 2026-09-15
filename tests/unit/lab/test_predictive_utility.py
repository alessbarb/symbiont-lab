from __future__ import annotations

from symbiont_lab.studies.learning.predictive_utility import (
    PredictiveUtilityOutcome,
    PredictiveUtilityStudyResult,
    run_predictive_utility_study,
    run_predictive_utility_trial,
)


def test_predictive_utility_trial_learns_and_beats_baselines():
    outcome = run_predictive_utility_trial(seed=101, ticks=350, eval_window=70)

    assert isinstance(outcome, PredictiveUtilityOutcome)
    assert outcome.horizon_ticks == 1
    assert outcome.target_id == "s"

    # 1. Improvement over early training phase (learning curve convergence)
    assert outcome.late_loss < outcome.early_loss

    # 2. Outperforms all trivial baselines
    assert outcome.loss_gain_vs_zero > 0.0
    assert outcome.loss_gain_vs_mean > 0.0
    assert outcome.loss_gain_vs_persist > 0.0
    assert outcome.late_loss < outcome.zero_baseline_loss
    assert outcome.late_loss < outcome.mean_baseline_loss
    assert outcome.late_loss < outcome.persist_baseline_loss

    # 3. Ablation 1: Plasticity ablation proves learning is plastic
    assert outcome.plasticity_utility_gain > 0.0
    assert outcome.late_loss < outcome.ablation_plasticity_loss

    # 4. Ablation 2: Structural lesion proves functional dependence on the edge
    assert outcome.structural_utility_gain > 0.0
    assert outcome.late_loss < outcome.ablation_lesion_loss

    # 5. Adapted weight matches expected negative coupling
    assert outcome.final_predictive_weight < -0.5


def test_predictive_utility_study_replicates_across_seeds():
    seeds = (101, 127, 149)
    result = run_predictive_utility_study(seeds=seeds, ticks=300)

    assert isinstance(result, PredictiveUtilityStudyResult)
    assert len(result.outcomes) == 3
    assert result.mean_loss_gain_vs_zero > 0.0
    assert result.mean_loss_gain_vs_mean > 0.0
    assert result.mean_loss_gain_vs_persist > 0.0
    assert result.mean_plasticity_gain > 0.0
    assert result.mean_structural_gain > 0.0

    # Every single seed must achieve positive predictive gain over all baselines & ablations
    for o in result.outcomes:
        assert o.loss_gain_vs_zero > 0.0
        assert o.loss_gain_vs_persist > 0.0
        assert o.plasticity_utility_gain > 0.0
        assert o.structural_utility_gain > 0.0

    # Serialization contract
    raw = result.as_dict()
    assert raw["seeds"] == [101, 127, 149]
    assert len(raw["outcomes"]) == 3
    assert "mean_plasticity_gain" in raw
