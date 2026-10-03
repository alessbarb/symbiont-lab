"""Unused source-trust prototype implementations stay deleted."""

from importlib.util import find_spec

import symbiont.core as core


def test_deleted_source_trust_modules_are_not_importable() -> None:
    assert find_spec("symbiont.core.social.evidence_trust") is None
    assert find_spec("symbiont.core.social.source_evidence") is None


def test_deleted_source_trust_types_are_not_exported_by_core() -> None:
    assert not hasattr(core, "EvidenceTrust")
    assert not hasattr(core, "SourceEvidenceOutcome")
    assert not hasattr(core, "SourceEvidenceSample")
    assert not hasattr(core, "SourceEvidenceState")
