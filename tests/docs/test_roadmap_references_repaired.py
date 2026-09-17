from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_spans_both_references_link_the_history_log_too():
    organism = (REPO_ROOT / "ORGANISM.md").read_text(encoding="utf-8")
    assert "docs/roadmap.md" in organism
    assert "docs/history/roadmap-log.md" in organism

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/history/roadmap-log.md" in readme
