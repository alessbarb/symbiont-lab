import pytest

from symbiont.heritage_stress_study import (
    HERITAGE_DIAGNOSTICS,
    PERFORMANCE_METRICS,
    run_replicated_heritage_stress_study,
)


def test_replicated_heritage_stress_is_deterministic_and_paired():
    first = run_replicated_heritage_stress_study(
        source_seeds=(3, 7, 11),
        target_offset=1009,
        hosts=18,
        steps=120,
        threat_rate=0.06,
        heritage_limit=8,
    )
    second = run_replicated_heritage_stress_study(
        source_seeds=(3, 7, 11),
        target_offset=1009,
        hosts=18,
        steps=120,
        threat_rate=0.06,
        heritage_limit=8,
    )

    assert first == second
    assert first.target_seeds == tuple(seed + 1009 for seed in first.source_seeds)
    assert first.conditions == ("naive", "learned", "inverted", "misaligned")
    assert len(first.world_digests) == len(first.source_seeds)
    assert len(first.source_pattern_counts) == len(first.source_seeds)
    assert "naive" not in first.paired_vs_naive

    for condition, metrics in first.paired_vs_naive.items():
        assert condition in {"learned", "inverted", "misaligned"}
        assert set(metrics) == set(PERFORMANCE_METRICS)
        for delta in metrics.values():
            assert 0 <= delta.pairs <= len(first.source_seeds)
            if delta.direction_agreement is not None:
                assert 0 <= delta.direction_agreement <= 1


def test_summaries_keep_performance_and_heritage_diagnostics_separate():
    study = run_replicated_heritage_stress_study(
        source_seeds=(5, 9),
        target_offset=1009,
        hosts=16,
        steps=110,
        threat_rate=0.06,
        heritage_limit=8,
    )

    expected = set(PERFORMANCE_METRICS) | set(HERITAGE_DIAGNOSTICS)
    for summary in study.summaries.values():
        assert set(summary.metrics) == expected
        assert summary.runs == 2

    naive = study.summaries["naive"].metrics
    assert naive["prior_mae"].mean is None
    assert naive["combined_mae"].defined_runs == 0
    assert naive["reexport_rate"].mean is None


def test_paired_performance_delta_matches_difference_when_all_pairs_defined():
    study = run_replicated_heritage_stress_study(
        source_seeds=(2, 6),
        target_offset=1009,
        hosts=20,
        steps=130,
        threat_rate=0.06,
        heritage_limit=8,
    )

    for condition in ("learned", "inverted", "misaligned"):
        for metric in PERFORMANCE_METRICS:
            delta = study.paired_vs_naive[condition][metric]
            candidate = study.summaries[condition].metrics[metric]
            baseline = study.summaries["naive"].metrics[metric]
            if (
                delta.pairs == len(study.source_seeds)
                and candidate.defined_runs == len(study.source_seeds)
                and baseline.defined_runs == len(study.source_seeds)
            ):
                assert candidate.mean is not None
                assert baseline.mean is not None
                assert delta.mean == pytest.approx(candidate.mean - baseline.mean)


def test_each_source_target_pair_keeps_one_fixed_world_across_conditions():
    study = run_replicated_heritage_stress_study(
        source_seeds=(4, 8, 12),
        target_offset=1009,
        hosts=14,
        steps=100,
        threat_rate=0.06,
        heritage_limit=6,
    )

    assert len(study.world_digests) == 3
    assert all(len(digest) == 64 for digest in study.world_digests)
    assert len(set(study.target_seeds)) == 3


def test_invalid_source_set_and_target_offset_are_rejected():
    with pytest.raises(ValueError):
        run_replicated_heritage_stress_study(source_seeds=())
    with pytest.raises(ValueError):
        run_replicated_heritage_stress_study(source_seeds=(1,), target_offset=0)
    with pytest.raises(ValueError):
        run_replicated_heritage_stress_study(source_seeds=range(51), hosts=2, steps=5)


def test_target_seed_colliding_with_a_source_seed_is_rejected():
    with pytest.raises(ValueError):
        run_replicated_heritage_stress_study(
            source_seeds=(3, 1012),
            target_offset=1009,
            hosts=2,
            steps=5,
        )
