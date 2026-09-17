from __future__ import annotations

from .conftest import REPO_ROOT, VALID_TYPES


def test_fuentes_declares_the_taxonomy():
    text = (REPO_ROOT / "docs" / "web" / "FUENTES.md").read_text(encoding="utf-8")
    for type_name in VALID_TYPES:
        assert type_name in text, f"FUENTES.md missing source type: {type_name}"
    assert "docs/_internal" not in text, (
        "FUENTES.md must not name docs/_internal/ (deleted; no longer a "
        "citable working directory in this repository)"
    )
    assert "| Claim ID |" in text, "FUENTES.md must declare the claim table header"
