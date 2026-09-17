from __future__ import annotations

import pytest

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
