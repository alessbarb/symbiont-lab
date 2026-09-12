from symbiont.core.model import Observation
from symbiont.simulation import EventContext
from symbiont_lab.studies.evidence.second_look import (
    run_second_look_study,
    second_look_measurement,
)


def _event(label: str, is_threat: bool) -> EventContext:
    return EventContext(
        step=12,
        host_index=3,
        truth_label=label,
        is_threat=is_threat,
        phase="pre_drift",
        drift_state="pre_drift",
        observation=Observation(0.2, 0.3, 0.2, 0.15, 0.08),
    )


def test_second_look_measurement_is_deterministic_and_bounded():
    event = _event("pathogen:stealth_sim", True)
    first = second_look_measurement(event, seed=17, noise=0.18)
    second = second_look_measurement(event, seed=17, noise=0.18)

    assert first == second
    assert 0 <= first <= 1


def test_second_look_study_uses_exact_equal_budget():
    study = run_second_look_study(
        hosts=20,
        steps=120,
        seed=13,
        threat_rate=0.05,
        budget=25,
    )

    assert study.budget == 25
    assert len(study.outcomes) == 5
    assert all(outcome.selected == 25 for outcome in study.outcomes)
    assert {outcome.strategy for outcome in study.outcomes} == {
        "risk",
        "novelty",
        "risk_novelty",
        "shadow_curiosity",
        "random",
    }


def test_second_look_study_is_deterministic():
    first = run_second_look_study(
        hosts=18,
        steps=110,
        seed=19,
        threat_rate=0.06,
        sensor_noise=0.20,
    )
    second = run_second_look_study(
        hosts=18,
        steps=110,
        seed=19,
        threat_rate=0.06,
        sensor_noise=0.20,
    )

    assert first == second


def test_outcomes_report_information_and_error_changes_without_assuming_benefit():
    study = run_second_look_study(
        hosts=30,
        steps=160,
        seed=11,
        threat_rate=0.06,
        budget=80,
    )

    for outcome in study.outcomes:
        assert outcome.pre_brier is not None
        assert outcome.post_brier is not None
        assert outcome.brier_gain is not None
        assert outcome.mean_entropy_reduction is not None
        assert outcome.mean_measurement is not None
        assert 0 <= outcome.pre_brier <= 1
        assert 0 <= outcome.post_brier <= 1
        assert 0 <= outcome.mean_measurement <= 1
        assert outcome.corrected_errors >= 0
        assert outcome.introduced_errors >= 0
        assert outcome.stealth_selected >= outcome.stealth_corrected


def test_zero_budget_is_explicitly_undefined_not_fabricated_zero_quality():
    study = run_second_look_study(
        hosts=8,
        steps=60,
        seed=5,
        threat_rate=0.05,
        budget=0,
    )

    for outcome in study.outcomes:
        assert outcome.selected == 0
        assert outcome.pre_brier is None
        assert outcome.post_brier is None
        assert outcome.brier_gain is None
        assert outcome.selected_threat_share is None
