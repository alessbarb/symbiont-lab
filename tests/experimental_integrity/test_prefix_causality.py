from __future__ import annotations

from symbiont_lab.studies.attention.causal import run_causal_attention_budget


def test_causal_attention_prefix_integrity():
    """Prefix invariance: causal selections are bounded by budget."""
    analysis = run_causal_attention_budget(
        hosts=30,
        steps=100,
        seed=42,
        budget_per_1000=12.0,
    )
    assert len(analysis.outcomes) == 4  # 4 strategies
    for outcome in analysis.outcomes:
        assert outcome.selected <= outcome.budget
