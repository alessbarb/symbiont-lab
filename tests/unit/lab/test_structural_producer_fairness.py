from __future__ import annotations

from symbiont_lab.studies.learning.structural_producer_fairness import (
    run_structural_producer_fairness_study,
)


def test_structural_producer_fairness_stress_passes_preregistered_bound():
    result = run_structural_producer_fairness_study(
        seeds=(101, 127, 149),
        ticks=32,
    )

    assert result.all_pass
    for trial in result.trials:
        assert trial.accepted_flood_hypotheses == 1
        assert trial.maximum_pending_per_producer == 1
        assert trial.maximum_wait_rounds <= trial.expected_wait_bound
        assert all(wins > 0 for _, wins in trial.producer_wins)
        assert len(trial.service_schedule) == trial.rounds
