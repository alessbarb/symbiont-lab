from symbiont_lab.studies.learning.cultural_foundation import run_cultural_foundation_study


def test_preregistered_cultural_foundation_protocol_is_replayable():
    result = run_cultural_foundation_study(seeds=(101, 127, 149), ticks=64)
    assert result.all_gates_pass
    assert result.replay_deterministic
    assert all(item.replay_valid for item in result.per_seed)
    assert all(item.independent_roots == 1 for item in result.per_seed)
