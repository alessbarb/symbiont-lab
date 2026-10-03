from __future__ import annotations

from lab.studies.learning.generative_cognition_release import (
    run_generative_cognition_release_gates,
)


def test_generative_cognition_release_gates_pass_and_are_reproducible() -> None:
    first = run_generative_cognition_release_gates(episodes=8)
    second = run_generative_cognition_release_gates(episodes=8)

    assert first.passed
    assert first.gc_e5.passed
    assert first.gc_e10.passed
    assert first.gc_e13.passed

    assert first.gc_e5.factual_contamination_count == 0
    assert first.gc_e10.agenda_contamination_count == 0
    assert first.gc_e13.source_diversity >= 2
    assert first.gc_e13.cross_episode_reuse >= 1

    assert first.as_dict() == second.as_dict()
