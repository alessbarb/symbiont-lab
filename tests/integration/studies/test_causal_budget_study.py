import pytest

from symbiont.causal_budget_study import run_replicated_causal_budget_study


def test_replicated_causal_study_is_deterministic_and_paired():
    first = run_replicated_causal_budget_study(
        seeds=(101, 127),
        budgets_per_1000=(8.0, 16.0),
        hosts=10,
        steps=80,
        threat_rate=0.05,
    )
    second = run_replicated_causal_budget_study(
        seeds=(101, 127),
        budgets_per_1000=(8.0, 16.0),
        hosts=10,
        steps=80,
        threat_rate=0.05,
    )

    assert first == second
    assert first.seeds == (101, 127)
    assert first.budgets_per_1000 == (8.0, 16.0)
    for budget in first.budgets_per_1000:
        assert len(first.absolute_budgets[budget]) == len(first.seeds)
        for strategy in first.strategies:
            assert first.summaries[budget][strategy].runs == len(first.seeds)


def test_replicated_causal_deltas_keep_seed_pairing():
    study = run_replicated_causal_budget_study(
        seeds=(101, 127, 149),
        budgets_per_1000=(12.0,),
        hosts=10,
        steps=90,
        threat_rate=0.06,
    )

    paired = study.paired_vs_reference[12.0]
    for strategy, metrics in paired.items():
        assert strategy != study.reference_strategy
        for metric, delta in metrics.items():
            assert delta.metric == metric
            assert delta.strategy == strategy
            assert delta.reference == study.reference_strategy
            assert 0 <= delta.pairs <= len(study.seeds)
            if delta.direction_agreement is not None:
                assert 0 <= delta.direction_agreement <= 1


def test_replicated_causal_study_rejects_duplicate_or_invalid_design():
    with pytest.raises(ValueError, match="unique"):
        run_replicated_causal_budget_study(seeds=(101, 101), hosts=2, steps=5)
    with pytest.raises(ValueError, match="unique"):
        run_replicated_causal_budget_study(
            seeds=(101,),
            budgets_per_1000=(12.0, 12.0),
            hosts=2,
            steps=5,
        )
    with pytest.raises(ValueError):
        run_replicated_causal_budget_study(
            seeds=(101,),
            budgets_per_1000=(-1.0,),
            hosts=2,
            steps=5,
        )
    with pytest.raises(ValueError):
        run_replicated_causal_budget_study(
            seeds=(101,),
            budgets_per_1000=(12.0,),
            reference_strategy="unknown",
            hosts=2,
            steps=5,
        )
