from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_internal_dir_exists_and_superpowers_gone():
    assert (REPO_ROOT / "docs" / "_internal").is_dir()
    assert not (REPO_ROOT / "docs" / "superpowers").exists()


def test_internal_readme_declares_non_normative():
    readme = REPO_ROOT / "docs" / "_internal" / "README.md"
    assert readme.is_file(), f"Not found: {readme}"
    text = readme.read_text(encoding="utf-8").lower()
    assert "non-normative" in text or "no normativ" in text
    assert "fuentes.md" in text or "docs/web" in text


# Files that legitimately keep the literal string "docs/superpowers":
# - this test file itself (it contains the sentinel string it greps for)
# - the two self-describing migration documents that narrate the *pre-move*
#   state as history (quoting the old path in prose, examples and shell
#   commands); rewriting them would be a semantic change, not a mechanical
#   path repair.
_ALLOWED_DANGLING_REFERENCES = {
    "tests/docs/test_internal_docs_not_authoritative.py",
    "docs/_internal/specs/2026-09-17-docs-reorg-web-publication-design.md",
    "docs/_internal/plans/2026-09-17-docs-reorg-and-web-scaffolding.md",
}


def test_no_dangling_superpowers_path_references():
    # Scan only git-tracked files, not the whole working tree: untracked,
    # gitignored local scratch (session memory logs, SDD process
    # directories, editor caches, ...) legitimately narrates or quotes this
    # migration in prose and varies per machine/session — it was never part
    # of the canonical documentation this check protects.
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.py", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    hits: list[str] = []
    for rel in tracked:
        if rel in _ALLOWED_DANGLING_REFERENCES:
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        if "docs/superpowers" in text:
            hits.append(rel)
    assert not hits, f"dangling docs/superpowers references: {hits}"
