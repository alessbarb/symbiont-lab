from __future__ import annotations

from symbiont_lab.studies.learning.embodied_counterfactual import (
    OpaqueLagCandidate,
    evaluate_frozen_counterfactual,
    fit_frozen_lag_predictors,
)


def test_frozen_fit_uses_only_the_training_prefix_and_predicts_paired_delta():
    actions = [[0.0], [1.0], [0.0], [1.0], [0.0], [1.0]]
    baseline = [[0.0], [0.0], [2.0], [0.0], [2.0], [0.0]]
    intervention = [[0.0], [0.0], [2.0], [0.0], [4.0], [0.0]]
    intervention_actions = [list(row) for row in actions]
    intervention_actions[3][0] = 2.0
    candidate = OpaqueLagCandidate(source_effector=0, target_receptor=0, lag=1)

    (predictor,) = fit_frozen_lag_predictors(
        actions, baseline, (candidate,), train_end=4
    )
    result = evaluate_frozen_counterfactual(
        predictor,
        baseline_observations=baseline,
        intervention_observations=intervention,
        baseline_actions=actions,
        intervention_actions=intervention_actions,
        intervention_tick=3,
    )

    assert predictor.slope == 2.0
    assert result.observed_intervention_delta == 2.0 / 3.0
    assert result.predicted_intervention_delta == 2.0 / 3.0
    assert result.intervention_prediction_error == 0.0


def test_candidate_set_is_fixed_and_empty_candidates_are_rejected():
    candidate = OpaqueLagCandidate(source_effector=2, target_receptor=4)
    predictors = fit_frozen_lag_predictors(
        [[0.0, 0.0, 0.0]] * 4,
        [[0.0] * 5] * 4,
        (candidate,),
        train_end=3,
    )

    assert tuple(item.candidate for item in predictors) == (candidate,)
