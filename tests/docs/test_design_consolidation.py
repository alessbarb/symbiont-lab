from __future__ import annotations

from .conftest import REPO_ROOT

DESIGN = REPO_ROOT / "docs" / "design"


def test_percepcion_y_embodiment_absorbs_three_sources_verbatim():
    assert not (DESIGN / "diseno-descubrimiento-senales-symbiont.md").exists()
    assert not (DESIGN / "digital-body-schema-and-emergent-morphology.md").exists()
    assert not (DESIGN / "recurrent-restoration-contract.md").exists()

    text = (DESIGN / "percepcion-y-embodiment.md").read_text(encoding="utf-8")
    assert "# Diseño técnico: significado emergente de señales en Symbiont" in text
    assert "# Digital Body Schema & Emergent Morphology" in text
    assert "# Contrato de restauración recurrente de Symbiont" in text


def test_cognicion_y_plasticidad_absorbs_three_sources_verbatim():
    assert not (DESIGN / "endogenous-plasticity.md").exists()
    assert not (DESIGN / "biological-memory-consolidation.md").exists()
    assert not (DESIGN / "canonical-birth-cognition.md").exists()

    text = (DESIGN / "cognicion-y-plasticidad.md").read_text(encoding="utf-8")
    assert "# Symbiont — diseño técnico de plasticidad endógena" in text
    assert "# Biological memory consolidation — v0.59.5 design" in text
    assert "# Canonical birth cognition" in text
