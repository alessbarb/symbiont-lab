from symbiont.core.collective_revision import revise_claim
from symbiont.core.evidence_trust import EvidenceTrust


def test_revision_preserves_dissent_instead_of_treating_majority_as_truth() -> None:
    strong = EvidenceTrust(1, 1, 1, 1, 1)
    weak = EvidenceTrust(0.2, 0.2, 0.2, 0.2, 0.2)

    result = revise_claim("signal", [(True, strong), (False, weak)])

    assert result.probability > 0.5
    assert result.dissent
    assert result.contributors == 2
