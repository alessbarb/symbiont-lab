"""Dormant source-trust prototypes are not aggregate core authorities."""

import symbiont.core as core


def test_dormant_source_trust_types_are_not_exported_by_core() -> None:
    assert not hasattr(core, "EvidenceTrust")
    assert not hasattr(core, "SourceEvidenceOutcome")
    assert not hasattr(core, "SourceEvidenceSample")
    assert not hasattr(core, "SourceEvidenceState")
