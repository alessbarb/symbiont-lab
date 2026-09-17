from __future__ import annotations

from .conftest import REPO_ROOT, VALID_TYPES


def test_fuentes_declares_the_taxonomy():
    text = (REPO_ROOT / "docs" / "web" / "FUENTES.md").read_text(encoding="utf-8")
    for type_name in VALID_TYPES:
        assert type_name in text, f"FUENTES.md missing source type: {type_name}"
    assert "docs/_internal" in text, "FUENTES.md must state _internal/ is prohibited as evidence"
    assert "| Claim ID |" in text, "FUENTES.md must declare the claim table header"
