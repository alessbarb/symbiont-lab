from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_portal_index_points_at_new_paths():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "releases/README.md" in text
    assert "releases/v0.80.15.md" not in text
    assert "history/roadmap-log.md" in text
    assert "_internal/plans" in text
    assert "superpowers/plans" not in text


def test_glossary_covers_organism_vocabulary():
    text = (REPO_ROOT / "docs" / "glossary.md").read_text(encoding="utf-8").lower()
    for term in ("organism", "genome", "phenotype", "habitat", "checkpoint", "percept"):
        assert term in text, f"glossary missing organism term: {term}"
