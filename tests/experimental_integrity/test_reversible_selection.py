from __future__ import annotations

import pytest

from symbiont_lab.studies.autonomous_life.reversible_selection import (
    CONTROL_ALLELE,
    HIGH_ALLELE,
    LOW_ALLELE,
    ReversibleSelectionStudy,
    _binomial_sf,
    _build_population,
    _mean_live_behavior_exploration,
    _run_one_seed,
    _sign,
    run_reversible_selection_study,
)
from symbiont_lab.studies.autonomous_life.harness import HarnessConfig


def test_mixed_founders_start_at_the_expected_mean_allele_value() -> None:
    config = HarnessConfig(
        population=8, generations=1, ticks=6, checkpoint_interval=6, random_checkpoint_count=0,
        seed=1, regimes=("scarcity", "abundance", "scarcity"), resource_scale=17.0,
    )
    founder_values = tuple([LOW_ALLELE] * 4 + [HIGH_ALLELE] * 4)
    harness = _build_population(config, founder_values=founder_values)
    mean = _mean_live_behavior_exploration(harness)
    assert mean == pytest.approx((4 * LOW_ALLELE + 4 * HIGH_ALLELE) / 8)


def test_control_founders_share_one_uniform_allele_value() -> None:
    config = HarnessConfig(
        population=8, generations=1, ticks=6, checkpoint_interval=6, random_checkpoint_count=0,
        seed=1, regimes=("scarcity", "abundance", "scarcity"), resource_scale=17.0,
    )
    founder_values = tuple([CONTROL_ALLELE] * 8)
    harness = _build_population(config, founder_values=founder_values)
    mean = _mean_live_behavior_exploration(harness)
    assert mean == pytest.approx(CONTROL_ALLELE)


def test_sign_helper_treats_small_values_as_zero() -> None:
    assert _sign(0.0) == 0
    assert _sign(1e-12) == 0
    assert _sign(0.01) == 1
    assert _sign(-0.01) == -1


def test_binomial_sf_matches_known_values() -> None:
    # P(X >= 0) is always 1 for any binomial distribution.
    assert _binomial_sf(10, 0, 0.5) == pytest.approx(1.0)
    # P(X >= n) under p=0.5 is 0.5 ** n.
    assert _binomial_sf(5, 5, 0.5) == pytest.approx(0.5 ** 5)


def test_run_one_seed_is_deterministic_for_the_same_seed() -> None:
    first = _run_one_seed(1, condition="mixed", population=8, ticks_per_segment=5)
    second = _run_one_seed(1, condition="mixed", population=8, ticks_per_segment=5)
    assert first == second


def test_run_one_seed_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError):
        _run_one_seed(1, condition="bogus", population=8, ticks_per_segment=5)


def test_small_study_runs_end_to_end_and_returns_bounded_shape() -> None:
    study = run_reversible_selection_study(
        seeds=(1, 2), ticks_per_segment=5, population=8, max_workers=1,
    )
    assert isinstance(study, ReversibleSelectionStudy)
    assert len(study.mixed_results) == 2
    assert len(study.control_results) == 2
    assert 0 <= study.mixed_reversals <= 2
    assert 0 <= study.control_reversals <= 2
    assert 0.0 <= study.mixed_reversal_p_value <= 1.0
    assert 0.0 <= study.control_reversal_p_value <= 1.0
    assert study.replay_deterministic is True
    for item in (*study.mixed_results, *study.control_results):
        assert item.final_population >= 0
        assert item.deaths >= 0


def test_run_rejects_duplicate_or_invalid_seeds() -> None:
    with pytest.raises(ValueError):
        run_reversible_selection_study(seeds=(1, 1), ticks_per_segment=5, population=8, max_workers=1)
    with pytest.raises(ValueError):
        run_reversible_selection_study(seeds=(True,), ticks_per_segment=5, population=8, max_workers=1)


def test_run_rejects_odd_or_out_of_bound_population() -> None:
    with pytest.raises(ValueError):
        run_reversible_selection_study(seeds=(1,), ticks_per_segment=5, population=7, max_workers=1)
    with pytest.raises(ValueError):
        run_reversible_selection_study(seeds=(1,), ticks_per_segment=5, population=4, max_workers=1)


def test_run_rejects_non_positive_ticks_per_segment() -> None:
    with pytest.raises(ValueError):
        run_reversible_selection_study(seeds=(1,), ticks_per_segment=0, population=8, max_workers=1)
