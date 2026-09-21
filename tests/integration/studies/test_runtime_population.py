from symbiont_lab.studies.runtime_population import run_runtime_population_study

def test_runtime_population_study_releases_dead_child_once() -> None:
    result = run_runtime_population_study()
    assert result.child_died
    assert result.live_after_death == 1
    assert result.slot_released
    assert result.duplicate_release_prevented
    assert result.capacity_blocked_birth
