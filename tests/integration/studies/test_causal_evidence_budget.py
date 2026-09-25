from symbiont_lab.studies.attention.causal import _online_indices
from symbiont_lab.studies.attention.retrospective import _ScoredEvent
from symbiont_lab.studies.evidence.causal_budget import (
    DIRECTED_STRATEGIES,
    _hybrid_indices,
    run_causal_evidence_budget,
    run_replicated_causal_evidence_study,
)


def _item(index: int) -> _ScoredEvent:
    return _ScoredEvent(
        event=None,
        risk=(index % 13) / 12,
        novelty=(index % 9) / 8,
        random_score=((index * 37) % 101) / 101,
    )


def test_zero_exploration_matches_existing_causal_selector_exactly():
    scored = [_item(index) for index in range(120)]
    for strategy in DIRECTED_STRATEGIES:
        legacy, legacy_forced = _online_indices(scored, strategy=strategy, budget=17)
        active, explored, active_forced = _hybrid_indices(
            scored,
            strategy=strategy,
            budget=17,
            exploration_fraction=0.0,
            seed=23,
        )
        assert active == legacy
        assert active_forced == legacy_forced
        assert explored == set()


def test_hybrid_selector_honors_exact_budget_and_exploration_quota_without_truth():
    scored = [_item(index) for index in range(200)]
    selected, explored, forced = _hybrid_indices(
        scored,
        strategy="risk",
        budget=40,
        exploration_fraction=0.20,
        seed=31,
    )
    assert len(selected) == 40
    assert len(set(selected)) == 40
    assert len(explored) == 8
    assert explored <= set(selected)
    assert forced >= 0


def test_causal_evidence_run_is_deterministic_and_equal_capacity():
    first = run_causal_evidence_budget(
        hosts=14,
        steps=100,
        seed=29,
        threat_rate=0.06,
        budget_per_1000=20,
        exploration_fractions=(0.0, 0.10),
        sensor_noise=0.18,
    )
    second = run_causal_evidence_budget(
        hosts=14,
        steps=100,
        seed=29,
        threat_rate=0.06,
        budget_per_1000=20,
        exploration_fractions=(0.0, 0.10),
        sensor_noise=0.18,
    )

    assert first == second
    assert len(first.world_digest) == 64
    assert {outcome.selected for outcome in first.outcomes} == {first.budget}
    assert len({outcome.condition for outcome in first.outcomes}) == len(first.outcomes)


def test_sensor_noise_cannot_change_world_or_selection_identity():
    low = run_causal_evidence_budget(
        hosts=12,
        steps=90,
        seed=41,
        threat_rate=0.06,
        budget_per_1000=20,
        exploration_fractions=(0.0, 0.10),
        sensor_noise=0.08,
    )
    high = run_causal_evidence_budget(
        hosts=12,
        steps=90,
        seed=41,
        threat_rate=0.06,
        budget_per_1000=20,
        exploration_fractions=(0.0, 0.10),
        sensor_noise=0.45,
    )

    assert low.world_digest == high.world_digest
    low_by_condition = {item.condition: item for item in low.outcomes}
    high_by_condition = {item.condition: item for item in high.outcomes}
    assert set(low_by_condition) == set(high_by_condition)
    for condition in low_by_condition:
        assert (
            low_by_condition[condition].selected_event_digest
            == high_by_condition[condition].selected_event_digest
        )
        assert low_by_condition[condition].pre_brier == high_by_condition[condition].pre_brier


def test_replicated_study_keeps_world_fixed_across_budgets_and_builds_paired_deltas():
    study = run_replicated_causal_evidence_study(
        seeds=(5, 11),
        budgets_per_1000=(10.0, 20.0),
        exploration_fractions=(0.0, 0.10),
        hosts=12,
        steps=90,
        threat_rate=0.06,
        sensor_noise=0.18,
    )

    assert len(study.world_digest) == 64
    assert set(study.world_digests) == {5, 11}
    assert set(study.summaries) == {10.0, 20.0}
    for budget in study.budgets_per_1000:
        assert study.paired_vs_random[budget]
        assert study.paired_vs_no_exploration[budget]
        assert len(study.absolute_budgets[budget]) == 2
        for condition, metrics in study.paired_vs_random[budget].items():
            assert condition != "random@explore=0.000"
            assert "post_recall" in metrics
            assert 0 <= metrics["post_recall"].pairs <= 2
