import pytest

from symbiont.evidence_noise_sweep import run_evidence_noise_sweep


def test_noise_sweep_is_deterministic_and_keeps_selection_fixed():
    first = run_evidence_noise_sweep(
        seeds=(211, 223),
        noise_levels=(0.08, 0.30),
        hosts=10,
        steps=80,
        threat_rate=0.05,
        budget_per_1000=15,
    )
    second = run_evidence_noise_sweep(
        seeds=(211, 223),
        noise_levels=(0.08, 0.30),
        hosts=10,
        steps=80,
        threat_rate=0.05,
        budget_per_1000=15,
    )

    assert first == second
    assert first.noise_levels == (0.08, 0.30)
    assert first.budget == round(10 * 80 * 15 / 1000)
    for noise in first.noise_levels:
        for strategy in first.strategies:
            assert first.summaries[noise][strategy].runs == 2


def test_noise_sweep_pairs_higher_noise_against_lowest_level():
    sweep = run_evidence_noise_sweep(
        seeds=(211, 223, 239),
        noise_levels=(0.30, 0.08, 0.18),
        hosts=10,
        steps=90,
        threat_rate=0.06,
        budget_per_1000=20,
    )

    assert sweep.noise_levels == (0.08, 0.18, 0.30)
    assert set(sweep.paired_vs_lowest_noise) == {0.18, 0.30}
    for noise, strategies in sweep.paired_vs_lowest_noise.items():
        for strategy, metrics in strategies.items():
            for metric, delta in metrics.items():
                assert delta.noise == noise
                assert delta.reference_noise == 0.08
                assert delta.strategy == strategy
                assert delta.metric == metric
                assert 0 <= delta.pairs <= len(sweep.seeds)


def test_noise_sweep_rejects_invalid_replication_design():
    with pytest.raises(ValueError, match="unique"):
        run_evidence_noise_sweep(seeds=(211, 211), hosts=2, steps=5)
    with pytest.raises(ValueError, match="unique"):
        run_evidence_noise_sweep(
            seeds=(211,),
            noise_levels=(0.18, 0.18),
            hosts=2,
            steps=5,
        )
    with pytest.raises(ValueError):
        run_evidence_noise_sweep(
            seeds=(211,),
            noise_levels=(0.0,),
            hosts=2,
            steps=5,
        )
    with pytest.raises(ValueError):
        run_evidence_noise_sweep(
            seeds=(211,),
            noise_levels=(0.18,),
            hosts=2,
            steps=5,
            budget_per_1000=-1,
        )
