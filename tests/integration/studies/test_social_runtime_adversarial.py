from symbiont_lab.studies.social_runtime_adversarial import run_social_runtime_adversarial_study


def test_runtime_adversarial_study_is_bounded_and_deterministic() -> None:
    first = run_social_runtime_adversarial_study()
    assert first == run_social_runtime_adversarial_study()
    assert first.cooperation_granted == 0.5
    assert first.contention_granted == 2.5
    assert first.contention_granted < first.contention_requested
    assert first.isolated_opportunities == 1
    assert first.one_way_observations == 1
    assert first.rejected_exchange_blocked
    assert first.resumed_exchange_granted == 0.25
