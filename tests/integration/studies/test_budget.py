from symbiont.budget import THREAT_FAMILIES, run_attention_budget_analysis


def test_matched_budget_uses_exact_policy_attention_cost():
    analysis = run_attention_budget_analysis(
        hosts=20,
        steps=120,
        seed=13,
        threat_rate=0.05,
    )

    assert analysis.natural_budget >= 0
    assert len(analysis.matched) == 5
    assert analysis.matched[0].strategy == "policy"
    assert all(row.selected == analysis.natural_budget for row in analysis.matched)
    assert all(row.events == analysis.hosts * analysis.steps for row in analysis.matched)


def test_budget_analysis_is_deterministic_including_random_baseline():
    first = run_attention_budget_analysis(
        hosts=16,
        steps=110,
        seed=19,
        threat_rate=0.06,
    )
    second = run_attention_budget_analysis(
        hosts=16,
        steps=110,
        seed=19,
        threat_rate=0.06,
    )

    assert first == second


def test_budget_analysis_exposes_family_recall_and_benign_cost():
    analysis = run_attention_budget_analysis(
        hosts=30,
        steps=160,
        seed=11,
        threat_rate=0.06,
    )

    for row in analysis.matched:
        assert set(row.family_recall) == set(THREAT_FAMILIES)
        assert 0 <= row.investigations_per_1000 <= 1000
        if row.threat_recall is not None:
            assert 0 <= row.threat_recall <= 1
        if row.precision is not None:
            assert 0 <= row.precision <= 1
        if row.benign_special_share is not None:
            assert 0 <= row.benign_special_share <= 1

    policy = analysis.matched[0]
    assert policy.family_recall["pathogen:stealth_sim"] is not None


def test_curve_budgets_are_monotonic_and_bounded():
    analysis = run_attention_budget_analysis(
        hosts=12,
        steps=100,
        seed=23,
        threat_rate=0.05,
        curve_budgets_per_1000=(2.0, 5.0, 10.0, 20.0),
    )

    for points in analysis.curves.values():
        selected = [point.selected for point in points]
        assert selected == sorted(selected)
        assert selected[-1] <= analysis.hosts * analysis.steps
