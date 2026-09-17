from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.private_model_controls import _history, _normalize_seeds


def test_private_model_controls_accept_declarative_seed_list():
    assert _normalize_seeds([101, 127, 149]) == (101, 127, 149)


def test_private_model_controls_registered():
    assert get_protocol("learning.private-model-controls").__name__ == "run_private_model_controls_study"


def test_specificity_world_keeps_identity_out_of_model_facing_tokens():
    left = _history(organism_id="a", seed=101, ticks=64, rule=0)
    right = _history(organism_id="b", seed=101, ticks=64, rule=1)

    assert len(left) == len(right) == 64
    assert tuple(record.context_tokens for record in left) == tuple(record.context_tokens for record in right)
    assert tuple(record.action_token for record in left) == tuple(record.action_token for record in right)
    assert any(l.outcome_tokens != r.outcome_tokens for l, r in zip(left, right))
    assert all("a" not in token and "b" not in token for record in (*left, *right)
               for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens))


def test_regime_control_changes_contingency_not_observation_vocabulary():
    pre = _history(organism_id="regime", seed=127, ticks=64, rule=0)
    post = _history(organism_id="regime", seed=127, ticks=64, rule=1)

    pre_vocab = {token for record in pre for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)}
    post_vocab = {token for record in post for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)}
    assert pre_vocab == post_vocab
    assert any(l.outcome_tokens != r.outcome_tokens for l, r in zip(pre, post))
