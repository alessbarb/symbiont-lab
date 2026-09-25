from __future__ import annotations

from .conftest import CHAPTERS, REPO_ROOT


def test_readme_lists_every_chapter_and_three_reading_paths():
    text = (REPO_ROOT / "docs" / "explanation" / "concepts" / "README.md").read_text(encoding="utf-8")
    for chapter in CHAPTERS:
        assert chapter in text, f"README missing link to {chapter}"
    for path_name in ("Lector curioso", "Investigador", "Implementador"):
        assert path_name in text, f"README missing reading path: {path_name}"
    assert "milestone" not in text.lower(), "no project-management vocabulary in docs/explanation/concepts/"
