from pathlib import Path


def test_signal_knowledge_renderer_consumes_projected_claim_fields():
    source = (Path(__file__).parents[1] / "render" / "signal-knowledge.js").read_text()

    assert "claim.evidenceCount" in source
    assert "claim.validationOpportunities" in source
    assert "claim.reasonClass" in source
    assert "claim.revision" in source
    assert "claim.evidence_count" not in source
    assert "claim.revision ??" in source


def test_cognition_renderer_surfaces_bounded_developmental_metrics():
    source = (Path(__file__).parents[1] / "render" / "cognition.js").read_text()

    assert "cognition-developmental-metrics" in (Path(__file__).parents[1] / "index.html").read_text()
    assert "cognition.structuralPressure ?? cognition.structural_pressure" in source
    assert "cognition.quantizationError ?? cognition.quantization_error" in source
    assert "cognition.relationChurn ?? cognition.relation_churn" in source
    assert "cognition.developmentalDivergence ?? cognition.developmental_divergence" in source
    assert "Number.isFinite(value)" in source


def test_signal_knowledge_autonomous_notebook():
    source = (Path(__file__).parents[1] / "render" / "signal-knowledge.js").read_text()
    assert "Cuaderno Científico de Hipótesis" in source
    assert "hypothesis-summary-bar" in source
    assert "hypothesis-card" in source
    assert "Bitácora de Eventos Epistemológicos" in source

