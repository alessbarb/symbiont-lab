from __future__ import annotations

import subprocess

from .conftest import REPO_ROOT

# Bare filenames, not full paths: docs/web/06-08 cite the old files both
# as `docs/design/X.md` (display text) and `../design/X.md` (link target)
# on the same line — a full-path substring check would miss the second
# form. Matching the bare filename catches both.
OLD_PATHS = [
    "endogenous-plasticity.md",
    "biological-memory-consolidation.md",
    "reproduction-death-population.md",
    "milestone-k-sociabilidad-emergente.md",
    "milestone-j-desarrollo-predictivo.md",
    "diseno-descubrimiento-senales-symbiont.md",
    "digital-body-schema-and-emergent-morphology.md",
    "recurrent-restoration-contract.md",
    "canonical-birth-cognition.md",
    "milestone-i-fisiologia-integrada.md",
    "cultural-foundation-v1.md",
    "private-slm-and-cultural-foundation.md",
    "cumulative-culture-v1.md",
]

# Each of the 5 merged docs/design/*.md files opens with a one-line
# provenance header of the form `> Consolidated from: a.md, b.md, c.md`
# naming the deleted files it absorbed (Tasks 2-6). That header is
# intentional prose, not a dangling reference (it isn't a link and the
# files it names really were merged into the file it appears in) — the
# repo's `tests/docs/test_design_consolidation.py` already pins its
# presence via the absorbed sources' verbatim headings. Excluding only
# this exact line shape keeps the rest of the sweep strict: a real
# dangling link anywhere else in these files (like the self-reference
# regression this test also guards against) still fails loudly.
_PROVENANCE_PREFIX = "> Consolidated from:"

# Same convention as tests/docs/test_internal_docs_not_authoritative.py:
# docs/_internal/ is declared non-normative (see that directory's own
# README) and its specs/plans intentionally narrate pre-consolidation
# history in prose and shell examples, quoting the old filenames verbatim.
# Rewriting them would be a semantic edit to a historical record, not a
# mechanical path repair, so the whole tree is out of scope here exactly
# as it is for that sibling test.
_EXCLUDED_PREFIXES = ("docs/_internal/",)

# These tests assert the OLD_PATHS names are absent from disk / absent
# from other docs — they legitimately mention the old filenames as string
# literals to do that, not as live references.
_EXCLUDED_FILES = {
    "tests/docs/test_design_consolidation.py",
    "tests/docs/test_web_no_milestone_vocabulary.py",
    "tests/docs/test_biological_memory_citations.py",
}


def test_no_tracked_file_references_an_old_design_path():
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.py", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    hits: list[str] = []
    for rel in tracked:
        if rel == "tests/docs/test_design_reference_repair.py":
            continue
        if rel in _EXCLUDED_FILES:
            continue
        if rel.startswith(_EXCLUDED_PREFIXES):
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if line.strip().startswith(_PROVENANCE_PREFIX):
                continue
            for old_path in OLD_PATHS:
                if old_path in line:
                    hits.append(f"{rel}:{line_no}: {old_path}")

    assert not hits, "dangling old design/ path references:\n" + "\n".join(hits)


def test_design_readme_indexes_the_five_new_files():
    text = (REPO_ROOT / "docs" / "design" / "README.md").read_text(encoding="utf-8")
    for new_file in (
        "percepcion-y-embodiment.md",
        "cognicion-y-plasticidad.md",
        "fisiologia-y-reproduccion.md",
        "sociabilidad-y-desarrollo-predictivo.md",
        "futuro-cultural.md",
    ):
        assert new_file in text, f"docs/design/README.md missing index entry: {new_file}"


def test_design_readme_index_entries_are_clickable_links():
    # A bare backticked filename (e.g. `` `percepcion-y-embodiment.md` ``)
    # is not clickable — the old index rendered every catalog entry as a
    # real markdown link, `[`X.md`](X.md)`. A prior rewrite of this file
    # regressed to plain non-linked headings while still containing the
    # filename string, which let the presence-only check above pass
    # vacuously. Assert the actual link-target syntax `](X.md)` is
    # present for each entry so that regression can't recur silently.
    text = (REPO_ROOT / "docs" / "design" / "README.md").read_text(encoding="utf-8")
    for new_file in (
        "percepcion-y-embodiment.md",
        "cognicion-y-plasticidad.md",
        "fisiologia-y-reproduccion.md",
        "sociabilidad-y-desarrollo-predictivo.md",
        "futuro-cultural.md",
    ):
        assert f"]({new_file})" in text, (
            f"docs/design/README.md index entry for {new_file} is not a "
            "clickable markdown link (expected a `](...)` link target)"
        )
