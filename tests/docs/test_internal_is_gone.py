from __future__ import annotations

from .conftest import REPO_ROOT


def test_internal_directory_does_not_exist():
    assert not (REPO_ROOT / "docs" / "_internal").exists()


def test_fuentes_no_longer_names_a_nonexistent_prohibited_directory():
    text = (REPO_ROOT / "docs" / "explanation" / "concepts" / "SOURCES.md").read_text(
        encoding="utf-8"
    )
    assert "docs/_internal" not in text
