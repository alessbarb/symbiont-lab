import pytest

from symbiont.core.evidence_trust import EvidenceTrust


def test_dimensions_remain_separate_and_aggregate_is_derived() -> None:
    trust = EvidenceTrust(1.0, 0.5, 0.0, 1.0, 0.5)

    assert trust.compatibility == 1.0
    assert trust.freshness == 0.0
    assert trust.aggregate == 0.6


def test_dimensions_are_bounded() -> None:
    with pytest.raises(ValueError):
        EvidenceTrust(1.1, 0.5, 0.5, 0.5, 0.5)
