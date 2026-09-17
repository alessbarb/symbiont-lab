from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.private_model_regime_shift import (
    _OUTCOME_PERMUTATION,
    _history,
    _normalize_seeds,
)


def test_symmetric_regime_protocol_registered():
    assert get_protocol("learning.private-model-regime-symmetric").__name__ == (
        "run_private_model_symmetric_regime_study"
    )


def test_symmetric_regime_accepts_declarative_seed_list():
    assert _normalize_seeds([101, 127, 149]) == (101, 127, 149)


def test_shift_preserves_context_action_surface_and_permuted_outcome_multiset():
    pre = _history(organism_id="o", seed=101, ticks=128, shifted=False)
    post = _history(organism_id="o", seed=101, ticks=128, shifted=True)

    assert tuple(record.context_tokens for record in pre) == tuple(record.context_tokens for record in post)
    assert tuple(record.action_token for record in pre) == tuple(record.action_token for record in post)

    pre_outcomes = [int(record.outcome_tokens[0].split(".")[-1]) for record in pre]
    post_outcomes = [int(record.outcome_tokens[0].split(".")[-1]) for record in post]
    assert post_outcomes == [_OUTCOME_PERMUTATION[value] for value in pre_outcomes]
    assert sorted(pre_outcomes) == sorted(_OUTCOME_PERMUTATION.index(value) for value in post_outcomes)


def test_shift_is_non_identity_bijection():
    assert sorted(_OUTCOME_PERMUTATION) == list(range(len(_OUTCOME_PERMUTATION)))
    assert any(index != value for index, value in enumerate(_OUTCOME_PERMUTATION))
