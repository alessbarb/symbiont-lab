from pathlib import Path

from symbiont_lab.studies.learning.autonomous_cultural_agency import run_autonomous_cultural_agency_study


def test_preregistered_autonomous_agency_replays_and_has_no_planner_result():
    result = run_autonomous_cultural_agency_study(seeds=(101, 127, 149), ticks=24, contact_rounds=8)
    assert result.all_gates_pass
    assert result.replay_deterministic
    assert result.aca10_cumulative_without_planner
    assert all(item.autonomous_solution for item in result.per_seed)
    assert all(item.transmission_attempts < item.cultural_opportunities for item in result.per_seed)
    assert all(item.multi_contributor_composites > 0 for item in result.per_seed)


def test_autonomous_treatment_has_no_content_planner_or_truth_input():
    source = Path("src/symbiont_lab/studies/learning/autonomous_cultural_agency.py").read_text(encoding="utf-8")

    # The study may evaluate outcomes, but its treatment must not choose
    # content or invoke the explicit content-bearing composition API.
    assert "compose_cultural_claims(" not in source
    assert "ground_truth" not in source
    assert "claim_id=" not in source
    assert "composite_id=" not in source
