from symbiont_lab.studies.learning.cumulative_culture import run_cumulative_culture_study


def test_preregistered_cumulative_culture_protocol_replays_and_passes():
    result = run_cumulative_culture_study(seeds=(101, 127, 149), ticks=128)
    assert result.all_gates_pass
    assert result.replay_deterministic
    assert all(item.replay_valid for item in result.per_seed)
    assert all(item.final_component_count == 3 for item in result.per_seed)
    assert all(item.independent_roots == 3 for item in result.per_seed)
    assert all(not item.tradition_only_solution and item.cumulative_solution for item in result.per_seed)
