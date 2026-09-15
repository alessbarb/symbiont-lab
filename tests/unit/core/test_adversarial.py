from symbiont.core.adversarial import AdversarialEcology


def test_stale_replay_and_poisoning_are_explicit() -> None:
    ecology = AdversarialEcology(max_age=2, max_sources=4)

    assert ecology.assess("a", 1, age=0).accepted
    assert not ecology.assess("a", 1, age=0).accepted
    stale = ecology.assess("b", 2, age=3)
    assert stale.stale and not stale.accepted
    assert ecology.assess("c", 3, age=0, contradiction=True).poisoning


def test_sybil_pressure_is_bounded() -> None:
    ecology = AdversarialEcology(max_sources=2)
    ecology.assess("a", 0, age=0)
    result = ecology.assess("b", 0, age=0)
    assert result.sybil_pressure == 1.0
