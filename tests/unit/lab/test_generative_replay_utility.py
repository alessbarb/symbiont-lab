from __future__ import annotations

from symbiont_lab.studies.learning.generative_replay_utility import (
    run_generative_replay_utility_study,
)


def test_replay_improves_prediction_without_new_factual_episode() -> None:
    result = run_generative_replay_utility_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.online_only_accuracy == 0.0
    assert result.replay_accuracy == 1.0
    assert result.replay_improves_prediction
    assert result.all_source_provenance_preserved
    assert result.all_factual_counts_unchanged
    assert result.all_factual_contamination_free
    assert result.all_agenda_contamination_free
    assert all(item.replay_root_origin == "replayed" for item in result.trials)


def test_replay_utility_gate_is_deterministic() -> None:
    first = run_generative_replay_utility_study().as_dict()
    second = run_generative_replay_utility_study().as_dict()

    assert first == second
