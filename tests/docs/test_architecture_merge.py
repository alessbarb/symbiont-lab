from __future__ import annotations

import re

from .conftest import REPO_ROOT

_MARKDOWN_LINK_RE = re.compile(r"\]\(([^)]+)\)")


def test_architecture_directory_and_old_file_are_gone():
    assert not (REPO_ROOT / "docs" / "architecture").exists()
    assert not (REPO_ROOT / "docs" / "artificial-life-model.md").exists()


def test_merged_architecture_file_contains_all_three_sources_verbatim():
    text = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    # One hard-to-fake line from each absorbed document:
    assert "El repositorio Symbiont Lab está estructurado como un monorepo" in text
    assert "## 1. Marco Epistemológico y Fundamento de Vida Artificial" in text
    assert "## Artificial life, not simulated biology" in text


def test_portal_index_points_at_merged_file():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/architecture.md" in text or "architecture.md" in text
    assert "architecture/entidad-symbiont.md" not in text
    assert "artificial-life-model.md" not in text or "docs/architecture.md" in text


def test_fuentes_taxonomy_points_at_merged_file():
    text = (REPO_ROOT / "docs" / "explanation" / "concepts" / "SOURCES.md").read_text(
        encoding="utf-8"
    )
    assert "docs/architecture.md" in text
    assert "docs/architecture/" not in text


def test_merged_architecture_file_relative_links_resolve():
    """Regression test for the merge-relocation link-depth bug.

    docs/architecture/README.md and docs/architecture/entidad-symbiont.md
    used to live two directories deep; docs/architecture.md (the merge
    target) lives one directory deep. Every relative link carried over
    verbatim from those two source files needed its ``../`` depth adjusted
    by exactly one level (``../../src/...`` -> ``../src/...``, and
    ``../adr/`` / ``../safety/`` / ``../design/`` / ``../math/`` -> bare
    ``adr/`` / ``safety/`` / ``design/`` / ``math/``). This test parses
    every markdown link in the merged file and asserts it resolves to a
    real file on disk from docs/architecture.md's own location, so a
    future re-merge or edit can't silently reintroduce the same
    depth-mismatch bug.
    """
    doc_path = REPO_ROOT / "docs" / "architecture.md"
    text = doc_path.read_text(encoding="utf-8")
    links = _MARKDOWN_LINK_RE.findall(text)
    assert links, "expected docs/architecture.md to contain markdown links"

    broken: list[str] = []
    checked = 0
    for link in links:
        if link.startswith(("http://", "https://", "#")):
            continue
        path_part = link.split("#", 1)[0]
        if not path_part:
            continue
        checked += 1
        target = (doc_path.parent / path_part).resolve()
        if not target.exists():
            broken.append(f"{link} -> {target}")

    assert checked > 60, f"expected 60+ resolvable local links, found {checked}"
    assert not broken, "broken relative link(s) in docs/architecture.md:\n" + "\n".join(broken)


def test_root_readme_points_at_merged_file():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "artificial-life-model.md" not in text
    assert "docs/architecture.md" in text


def test_web_readme_points_at_merged_file():
    text = (REPO_ROOT / "docs" / "explanation" / "concepts" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "docs/architecture/" not in text
    assert "docs/architecture.md" in text
