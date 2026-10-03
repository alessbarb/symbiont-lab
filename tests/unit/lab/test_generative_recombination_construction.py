from __future__ import annotations

from lab.studies.learning.generative_recombination_construction import (
    run_generative_recombination_construction_study,
)


def test_recombination_construction_gate_preserves_provenance_without_contamination() -> None:
    result = run_generative_recombination_construction_study(seeds=(101, 127, 149))

    assert result.passed
    assert result.treatment_construction_rate == 1.0
    assert result.provenance_preservation_rate == 1.0
    assert result.incompatible_rejection_rate == 1.0
    assert result.all_factual_contamination_free
    assert all(not item.control_constructed for item in result.results)


def test_recombination_construction_gate_is_deterministic() -> None:
    first = run_generative_recombination_construction_study(seeds=(101, 127, 149)).as_dict()
    second = run_generative_recombination_construction_study(seeds=(101, 127, 149)).as_dict()

    assert first == second
