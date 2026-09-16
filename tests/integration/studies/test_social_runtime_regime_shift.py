import pytest

from symbiont_lab.studies.social_runtime_regime_shift import run_social_runtime_regime_shift_study


def test_runtime_revises_resource_evidence_after_regime_shift() -> None:
    result = run_social_runtime_regime_shift_study(phase_ticks=8)
    assert result.pre_shift_successes == ("water",) * 7
    assert result.first_post_shift_resource == "food"
    assert result.new_resource_observed
    assert result.checkpoint_replay_equal
    assert result.continuation_replay_equal


def test_regime_shift_requires_a_bounded_phase() -> None:
    with pytest.raises(ValueError, match="phase_ticks"):
        run_social_runtime_regime_shift_study(phase_ticks=3)
