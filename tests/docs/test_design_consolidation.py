from __future__ import annotations

import pytest

from .conftest import REPO_ROOT

DESIGN = REPO_ROOT / "docs" / "design"


@pytest.mark.skip(reason="Obsolete after English migration")
def test_percepcion_y_embodiment_absorbs_three_sources_verbatim():
    assert not (DESIGN / "diseno-descubrimiento-senales-symbiont.md").exists()
    assert not (DESIGN / "digital-body-schema-and-emergent-morphology.md").exists()
    assert not (DESIGN / "recurrent-restoration-contract.md").exists()

    text = (DESIGN / "percepcion-y-embodiment.md").read_text(encoding="utf-8")
    assert "# Diseño técnico: significado emergente de señales en Symbiont" in text
    assert "# Digital Body Schema & Emergent Morphology" in text
    assert "# Contrato de restauración recurrente de Symbiont" in text


@pytest.mark.skip(reason="Obsolete after English migration")
def test_cognicion_y_plasticidad_absorbs_three_sources_verbatim():
    assert not (DESIGN / "endogenous-plasticity.md").exists()
    assert not (DESIGN / "biological-memory-consolidation.md").exists()
    assert not (DESIGN / "canonical-birth-cognition.md").exists()

    text = (DESIGN / "cognicion-y-plasticidad.md").read_text(encoding="utf-8")
    assert "# Symbiont — diseño técnico de plasticidad endógena" in text
    assert "# Biological memory consolidation — v0.59.5 design" in text
    assert "# Canonical birth cognition" in text


@pytest.mark.skip(reason="Obsolete after English migration")
def test_fisiologia_y_reproduccion_absorbs_two_sources_verbatim():
    assert not (DESIGN / "milestone-i-fisiologia-integrada.md").exists()
    assert not (DESIGN / "reproduction-death-population.md").exists()

    text = (DESIGN / "fisiologia-y-reproduccion.md").read_text(encoding="utf-8")
    assert "# Fisiología, ontogenia y reproducción canónica" in text


@pytest.mark.skip(reason="Obsolete after English migration")
def test_sociabilidad_y_desarrollo_predictivo_absorbs_two_sources_verbatim():
    assert not (DESIGN / "milestone-k-sociabilidad-emergente.md").exists()
    assert not (DESIGN / "milestone-j-desarrollo-predictivo.md").exists()

    text = (DESIGN / "sociabilidad-y-desarrollo-predictivo.md").read_text(encoding="utf-8")
    assert "# Milestone K — Sociabilidad emergente" in text
    assert "# Milestone J — Desarrollo predictivo autónomo" in text


@pytest.mark.skip(reason="Obsolete after English migration")
def test_futuro_cultural_absorbs_three_sources_verbatim():
    assert not (DESIGN / "cultural-foundation-v1.md").exists()
    assert not (DESIGN / "private-slm-and-cultural-foundation.md").exists()
    assert not (DESIGN / "cumulative-culture-v1.md").exists()

    text = (DESIGN / "futuro-cultural.md").read_text(encoding="utf-8")
    assert "# Cultural Foundation v1" in text
    assert "# Private SLM & Cultural Foundation" in text
    assert "# Cumulative Culture v1" in text


@pytest.mark.skip(reason="Obsolete after English migration")
def test_research_status_points_at_merged_file():
    text = (REPO_ROOT / "research" / "STATUS.md").read_text(encoding="utf-8")
    assert "docs/design/futuro-cultural.md" in text
    assert "cultural-foundation-v1.md" not in text
    assert "private-slm-and-cultural-foundation.md" not in text
    assert "cumulative-culture-v1.md" not in text
