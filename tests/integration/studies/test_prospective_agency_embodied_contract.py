from __future__ import annotations

from symbiont_lab.studies.learning.prospective_agency_embodied import (
    ProspectiveEmbodiedCondition,
    ProspectiveEmbodiedStudy,
    ProspectiveEmbodiedTrial,
)


def test_embodied_prospective_result_distinguishes_testability_from_outcome():
    non_testable = ProspectiveEmbodiedTrial(
        seed=101,
        warmup_ticks_requested=5000,
        readiness_found=False,
        readiness_tick=None,
        readiness_reason="no_prospective_selection",
        final_tick=0,
        first_cognitive_primitive_tick=None,
        first_primitive_readout_tick=None,
        active_model_id=None,
        motor_primitives=0,
        cognitive_primitives=0,
        primitive_readout_nodes=0,
        known_outcome_values=0,
        primitive_candidates=0,
        recurrent_primitive_candidates=0,
        max_primitive_samples=0,
        sample_gate_candidates=0,
        controllability_gate_candidates=0,
        variance_gate_candidates=0,
        direction_gate_candidates=0,
        full_competence_gate_candidates=0,
        best_candidate_controllability=0.0,
        best_candidate_directional_consistency=0.0,
        lowest_recurrent_effect_variance=None,
        cognitive_concepts=0,
        cognitive_readouts=0,
        structural_candidates=0,
        structural_producers=0,
        oldest_structural_wait_ticks=0,
        peak_structural_candidates=0,
        peak_structural_wait_ticks=0,
        conditions=(),
    )
    study = ProspectiveEmbodiedStudy(
        seeds=(101,),
        warmup_ticks=5000,
        horizon_ticks=256,
        trials=(non_testable,),
    )

    assert study.testable_trials == 0
    payload = study.as_dict()
    assert payload["testable_trials"] == 0
    assert payload["trials"][0]["readiness_found"] is False


def test_embodied_condition_keeps_homeostasis_primary_and_ecology_descriptive():
    condition = ProspectiveEmbodiedCondition(
        condition="full",
        applicable=True,
        ticks_completed=64,
        alive=True,
        start_homeostatic_deviation=0.8,
        end_homeostatic_deviation=0.5,
        homeostatic_change=-0.3,
        reserve_change=0.1,
        displacement_delta=0.2,
        resource_progress_delta=-0.4,
        absorbed_energy=2.0,
        prospective_selected_ticks=3,
        primitive_prospective_ticks=3,
    )

    payload = condition.as_dict()
    assert payload["homeostatic_change"] == -0.3
    assert payload["resource_progress_delta"] == -0.4
    assert payload["condition"] == "full"
