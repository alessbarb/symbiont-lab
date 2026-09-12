import pytest

from symbiont.evidence_study import EVIDENCE_METRICS, run_replicated_evidence_study


def test_replicated_evidence_study_is_deterministic_and_paired():
    first = run_replicated_evidence_study(
        seeds=(3, 7, 11),
        hosts=16,
        steps=100,
        threat_rate=0.05,
        budget=20,
    )
    second = run_replicated_evidence_study(
        seeds=(3, 7, 11),
        hosts=16,
        steps=100,
        threat_rate=0.05,
        budget=20,
    )

    assert first == second
    assert first.budgets == (20, 20, 20)
    assert first.reference_strategy == "random"
    assert set(first.summaries) == set(first.strategies)
    assert "random" not in first.paired_vs_reference

    for strategy, metrics in first.paired_vs_reference.items():
        assert strategy != "random"
        assert set(metrics) == set(EVIDENCE_METRICS)
        for delta in metrics.values():
            assert 0 <= delta.pairs <= len(first.seeds)
            if delta.direction_agreement is not None:
                assert 0 <= delta.direction_agreement <= 1


def test_natural_policy_budget_may_vary_by_seed_and_is_preserved():
    study = run_replicated_evidence_study(
        seeds=(2, 5, 9),
        hosts=12,
        steps=90,
        threat_rate=0.04,
        budget=None,
    )

    assert len(study.budgets) == 3
    assert all(budget >= 0 for budget in study.budgets)
    assert len(study.budgets_per_1000) == 3
    for summary in study.summaries.values():
        assert summary.runs == 3


def test_zero_budget_produces_undefined_quality_metrics_without_fake_deltas():
    study = run_replicated_evidence_study(
        seeds=(3, 7),
        hosts=8,
        steps=70,
        threat_rate=0.05,
        budget=0,
    )

    for summary in study.summaries.values():
        assert summary.metrics["brier_gain"].mean is None
        assert summary.metrics["net_correction_rate"].defined_runs == 0
    for metrics in study.paired_vs_reference.values():
        assert metrics["brier_gain"].mean is None
        assert metrics["brier_gain"].pairs == 0


def test_invalid_seed_set_and_reference_are_rejected():
    with pytest.raises(ValueError):
        run_replicated_evidence_study(seeds=())
    with pytest.raises(ValueError):
        run_replicated_evidence_study(
            seeds=(1,),
            hosts=4,
            steps=20,
            reference_strategy="oracle",
        )
    with pytest.raises(ValueError):
        run_replicated_evidence_study(seeds=range(51), hosts=2, steps=5)
