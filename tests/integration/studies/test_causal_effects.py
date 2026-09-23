from __future__ import annotations

import pytest

from symbiont_lab.physics3d.effects import PhysicalState, physical_consequence
from symbiont_lab.studies.physics3d.causal_effects import (
    MatchedControlTrial,
    analyze_matched_controls,
)


def _state(tick: int, x: float) -> PhysicalState:
    return PhysicalState(
        tick=tick,
        position_world=(x, 0.0, 1.0),
        orientation_world=(0.0, 0.0, 0.0, 1.0),
        linear_velocity_world=(0.0, 0.0, 0.0),
        angular_velocity_world=(0.0, 0.0, 0.0),
        center_of_mass_world=(x, 0.0, 1.0),
        contact_links=frozenset({1, 2}),
        joint_positions=((0, 0.0),),
    )


def _effect(distance: float, work: float):
    return physical_consequence(
        _state(0, 0.0),
        _state(4, distance),
        path_length=abs(distance),
        mechanical_work_joules=work,
    )


def test_matched_control_analysis_separates_passive_and_motor_control():
    initial = _state(0, 0.0)
    trial = MatchedControlTrial(
        trial_id="trial-1",
        primitive_id="primitive.example",
        initial_state=initial,
        primitive=_effect(0.10, 1.0),
        passive=_effect(0.02, 0.0),
        motor_control=_effect(0.03, 0.9),
    )

    report = analyze_matched_controls([trial])[0]
    assert report.trials == 1
    assert report.primitive_minus_passive_translation_mean[0] == pytest.approx(0.08)
    assert report.primitive_minus_motor_control_translation_mean[0] == pytest.approx(0.07)
    assert report.passive_adjusted_directional_concentration == pytest.approx(1.0)
    assert report.control_adjusted_directional_concentration == pytest.approx(1.0)


def test_matched_control_analysis_rejects_duplicate_trial_ids():
    initial = _state(0, 0.0)
    trial = MatchedControlTrial(
        trial_id="trial-1",
        primitive_id="primitive.example",
        initial_state=initial,
        primitive=_effect(0.10, 1.0),
        passive=_effect(0.02, 0.0),
        motor_control=_effect(0.03, 0.9),
    )

    with pytest.raises(ValueError, match="duplicate matched-control trial_id"):
        analyze_matched_controls([trial, trial])
