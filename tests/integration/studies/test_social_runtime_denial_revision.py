import pytest

from symbiont_lab.studies.social_runtime_denial_revision import (
    run_social_runtime_denial_revision_study,
)


def test_runtime_revises_after_repeated_denials_and_replays() -> None:
    result = run_social_runtime_denial_revision_study(phase_ticks=8)
    assert result.pre_shift_successes == ("beta",) * 7
    assert result.revision_tick is not None
    assert result.revision_tick < result.phase_ticks
    assert result.checkpoint_replay_equal
    assert result.continuation_replay_equal


def test_denial_revision_requires_a_bounded_phase() -> None:
    with pytest.raises(ValueError, match="phase_ticks"):
        run_social_runtime_denial_revision_study(phase_ticks=3)
