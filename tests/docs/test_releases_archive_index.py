from __future__ import annotations

import re

from .conftest import REPO_ROOT


def test_every_archived_release_is_indexed_exactly_once():
    archive_dir = REPO_ROOT / "docs" / "releases" / "archive"
    index_path = REPO_ROOT / "docs" / "releases" / "README.md"
    assert archive_dir.is_dir(), f"Not found: {archive_dir}"
    assert index_path.is_file(), f"Not found: {index_path}"

    archived = {p.name for p in archive_dir.glob("v*.md")}
    assert archived, "expected at least one archived release file"

    index_text = index_path.read_text(encoding="utf-8")
    counts = {name: len(re.findall(re.escape(name), index_text)) for name in archived}

    missing = [name for name, count in counts.items() if count == 0]
    duplicated = [name for name, count in counts.items() if count > 1]

    assert not missing, f"releases missing from README.md index: {sorted(missing)}"
    assert not duplicated, f"releases indexed more than once: {sorted(duplicated)}"


def test_no_loose_release_files_outside_archive():
    releases_dir = REPO_ROOT / "docs" / "releases"
    loose = [p.name for p in releases_dir.glob("v*.md")]
    assert not loose, f"release files must live under archive/, found loose: {loose}"
