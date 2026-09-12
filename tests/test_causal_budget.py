import pytest

from symbiont.budget import _ScoredEvent
from symbiont.causal_budget import STRATEGIES, _online_indices, run_causal_attention_budget


def _item(risk: float, novelty: float, random_score: float) -> _ScoredEvent:
    return _ScoredEvent(
        event=None,  # _online_indices deliberately needs no evaluator/event truth.
        risk=risk,
        novelty=novelty,
        random_score=random_score,
    )


def test_future_scores_cannot_change_prefix_decisions():
    prefix = [
        _item(0.10, 0.10, 0.11),
        _item(0.80, 0.20, 0.82),
        _item(0.30, 0.90, 0.33),
        _item(0.70, 0.50, 0.74),
    ]
    calm_future = [_item(0.05, 0.05, 0.20 + index * 0.01) for index in range(8)]
    extreme_future = [_item(0.99, 0.99, 0.90 - index * 0.01) for index in range(8)]

    for strategy in STRATEGIES:
        calm, _ = _online_indices(prefix + calm_future, strategy=strategy, budget=4)
        extreme, _ = _online_indices(prefix + extreme_future, strategy=strategy, budget=4)
        assert [index for index in calm if index < len(prefix)] == [
            index for index in extreme if index < len(prefix)
        ]


def test_all_causal_selectors_honor_same_ex_ante_budget():
    scored = [
        _item(
            risk=(index % 11) / 10,
            novelty=(index % 7) / 6,
            random_score=((index * 37) % 101) / 101,
        )
        for index in range(100)
    ]
    for strategy in STRATEGIES:
        indices, forced = _online_indices(scored, strategy=strategy, budget=13)
        assert len(indices) == 13
        assert len(set(indices)) == 13
        assert forced >= 0


def test_causal_budget_analysis_is_deterministic_and_matched():
    first = run_causal_attention_budget(
        hosts=12,
        steps=90,
        seed=19,
        threat_rate=0.05,
        budget_per_1000=15,
    )
    second = run_causal_attention_budget(
        hosts=12,
        steps=90,
        seed=19,
        threat_rate=0.05,
        budget_per_1000=15,
    )

    assert first == second
    assert {row.selected for row in first.outcomes} == {first.budget}
    assert {row.budget for row in first.outcomes} == {first.budget}


def test_negative_causal_budget_is_rejected():
    with pytest.raises(ValueError):
        run_causal_attention_budget(hosts=2, steps=5, budget_per_1000=-1)
