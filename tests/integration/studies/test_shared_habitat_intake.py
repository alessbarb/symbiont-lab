import pytest

from symbiont_lab.studies.shared_habitat_intake import run_shared_habitat_intake_study


def test_shared_habitat_intake_is_finite_and_replayable() -> None:
    result = run_shared_habitat_intake_study()
    assert result.first_granted == pytest.approx(0.75)
    assert result.second_granted == pytest.approx(0.25)
    assert result.remaining_resources == pytest.approx(0.0)
    assert result.capacity_limited
    assert result.checkpoint_replay_equal
