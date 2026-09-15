from symbiont_lab.studies.reproduction_runtime import run_runtime_reproduction_study

def test_runtime_reproduction_study_materializes_germinal_child_and_replays() -> None:
    result = run_runtime_reproduction_study(ticks=2)
    assert result.parent_id == "study-parent"
    assert result.child_id != result.parent_id
    assert result.generation == 1
    assert result.germinal_node_count == 0
    assert result.replay_equal
