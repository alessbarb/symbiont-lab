import math

import pytest

from symbiont_lab.studies.social_emergence import run_social_emergence_study


def test_seeded_emergence_study_is_replayable_and_has_no_isolated_member() -> None:
    first = run_social_emergence_study(seed=11, ticks=40)
    second = run_social_emergence_study(seed=11, ticks=40)
    assert first == second
    assert first.interactions == 40
    assert first.positive_relations + first.negative_relations + first.neutral_or_unknown > 0
    assert first.isolated_members == 0
    assert 1 <= first.unique_pairs <= first.interactions
    assert first.pair_entropy >= 0
    assert first.pair_entropy <= math.log(first.unique_pairs) + 1e-12


def test_emergence_study_rejects_invalid_population() -> None:
    with pytest.raises(ValueError):
        run_social_emergence_study(members=1)
