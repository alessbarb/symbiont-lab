import pytest

from symbiont_lab.studies.reproduction import run_reproduction_study


def test_reproduction_study_releases_once_and_ignores_duplicate_death() -> None:
    result = run_reproduction_study()
    assert (result.parent_count, result.offspring_count) == (2, 1)
    assert result.death_releases == 1
    assert result.duplicate_death_ignored
    assert result.remaining_budget == pytest.approx(1.0)


def test_reproduction_study_rejects_impossible_capacity() -> None:
    with pytest.raises(ValueError):
        run_reproduction_study(capacity=1)
