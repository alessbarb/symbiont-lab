from pathlib import Path


def test_signal_knowledge_renderer_consumes_projected_claim_fields():
    source = (Path(__file__).parents[1] / "render" / "signal-knowledge.js").read_text()

    assert "claim.evidenceCount" in source
    assert "claim.validationOpportunities" in source
    assert "claim.reasonClass" in source
    assert "claim.revision" in source
    assert "claim.evidence_count" not in source
    assert "claim.revision ??" in source
