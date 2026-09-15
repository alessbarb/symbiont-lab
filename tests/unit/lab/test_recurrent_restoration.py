from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.continuity.recurrent_restoration import (
    run_recurrent_restoration_study,
    run_restoration_continuity_trial,
)


def test_recurrent_restoration_protocol_is_registered():
    protocol = get_protocol("continuity.recurrent-restoration")
    assert protocol is run_recurrent_restoration_study


def test_level1_continuity_behavior():
    outcome = run_restoration_continuity_trial(seed=42)

    # Condition B (deepcopy) must have exact zero error across all ticks
    assert outcome.level1.condition_b_max_diff == 0.0

    # Condition D (exact weights, cold dynamic start) must converge geometrically to < 1e-4
    assert outcome.level1.condition_d_converged is True
    assert outcome.level1.condition_d_ticks_to_converge is not None
    assert outcome.level1.condition_d_ticks_to_converge <= 15
    assert outcome.level1.condition_d_late_mean_diff < 1e-5

    # Condition C (real checkpoint with quantized weights) does NOT converge to 1e-4
    assert outcome.level1.condition_c_converged is False
    assert outcome.level1.condition_c_late_mean_diff > 0.01


def test_level2_plasticity_continuity_behavior():
    outcome = run_restoration_continuity_trial(seed=123)

    # Condition B preserves weights and eligibility exactly
    assert outcome.level2.condition_b_weight_diff == 0.0
    assert outcome.level2.condition_b_eligibility_diff == 0.0

    # Condition D has small drift due to the transient Oja updates during initial ticks
    assert 0.0 < outcome.level2.condition_d_weight_diff < 0.01

    # Condition C has significantly larger drift because of initial weight quantization
    assert outcome.level2.condition_c_weight_diff > outcome.level2.condition_d_weight_diff * 5


def test_level3_ontogenesis_continuity_behavior():
    outcome = run_restoration_continuity_trial(seed=777)

    # Condition B maintains 100% topological parity with Condition A
    assert outcome.level3.condition_b_divergence_tick is None
    assert outcome.level3.condition_b_final_revision == outcome.level3.condition_a_final_revision

    # Condition C diverges topologically at the first consolidation tick following restart
    assert outcome.level3.condition_c_divergence_tick == 48


def test_recurrent_restoration_study_multi_seed():
    study = run_recurrent_restoration_study(seeds=(42, 123))

    assert len(study.outcomes) == 2
    assert study.level1_c_converged_fraction == 0.0
    assert study.level3_b_parity_rate == 1.0
    assert study.level3_c_immediate_divergence_rate == 1.0
    assert study.level2_c_mean_weight_drift > study.level2_d_mean_weight_drift

    serialized = study.as_dict()
    assert "outcomes" in serialized
    assert "level1_d_mean_ticks_to_converge" in serialized
    assert serialized["seeds"] == [42, 123]
