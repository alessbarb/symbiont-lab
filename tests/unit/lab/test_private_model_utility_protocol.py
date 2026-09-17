from __future__ import annotations

from types import SimpleNamespace

import pytest

import symbiont_lab.studies.learning.private_model_utility as protocol
from symbiont_lab.studies.learning.private_model_utility import _normalize_seeds


def test_private_model_utility_accepts_declarative_seed_list():
    assert _normalize_seeds([101, 127, 149]) == (101, 127, 149)


def test_private_model_utility_preserves_tuple_callers():
    assert _normalize_seeds((7, 11, 19)) == (7, 11, 19)


@pytest.mark.parametrize(
    "seeds",
    [[], [7, 7], [True], "7,11,19"],
)
def test_private_model_utility_rejects_invalid_seed_sequences(seeds):
    with pytest.raises(ValueError):
        _normalize_seeds(seeds)


def _family(architecture: str, *, loss: float, gain: float, promoted: bool, reason: str):
    return SimpleNamespace(
        architecture_id=SimpleNamespace(value=architecture),
        evaluation=SimpleNamespace(
            candidate=SimpleNamespace(mean_log_loss=loss),
            gain_over_trivial=gain,
        ),
        promotion=SimpleNamespace(promote=promoted, reason=reason),
    )


def test_private_model_utility_preserves_each_preregistered_seed(monkeypatch):
    calls: list[int] = []

    def fake_study(corpus, *, seed, **kwargs):
        del corpus, kwargs
        calls.append(seed)
        offset = seed / 10_000.0
        return SimpleNamespace(families=(
            _family("gru-v1", loss=1.8 + offset, gain=0.02 + offset, promoted=True, reason="held_out_gain"),
            _family(
                "transformer-v1",
                loss=1.7 + offset,
                gain=0.03 + offset,
                promoted=seed != 127,
                reason="held_out_gain" if seed != 127 else "insufficient_held_out_gain",
            ),
        ))

    monkeypatch.setattr(protocol, "run_model_family_study", fake_study)
    result = protocol.run_private_model_utility_study(seeds=[101, 127, 149], ticks=48)

    assert calls == [101, 127, 149]
    assert tuple(item.seed for item in result.per_seed) == (101, 127, 149)
    assert result.gru_promotions == 3
    assert result.transformer_promotions == 2
    middle = result.per_seed[1]
    assert middle.transformer_promoted is False
    assert middle.transformer_promotion_reason == "insufficient_held_out_gain"
    assert middle.transformer_gain_over_gru == pytest.approx(0.1)
