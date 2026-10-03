from __future__ import annotations

from lab.studies.learning.generative_consolidation_gates import (
    run_generative_consolidation_gates_study,
)


def test_consolidation_requires_use_and_source_diversity() -> None:
    result = run_generative_consolidation_gates_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.benefit_condition_submitted
    assert not result.no_generated_reuse_control_submitted
    assert not result.no_source_diversity_control_submitted
    assert result.repeated_replay_suppressed
    assert result.all_factual_contamination_free


def test_consolidation_gate_is_deterministic() -> None:
    assert (
        run_generative_consolidation_gates_study().as_dict()
        == run_generative_consolidation_gates_study().as_dict()
    )
