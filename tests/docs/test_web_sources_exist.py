# tests/docs/test_web_sources_exist.py
from __future__ import annotations

import re

import pytest

from .conftest import REPO_ROOT, VALID_TYPES

# TODO(deferred — pending chapter authoring): spec check 7 is NOT implemented
# here. Per the original docs-reorg-web-publication design spec's FUENTES.md
# section, verification-test list, item 7 (see git history for that spec's
# full text; the working-tree copy has been deleted):
#
#   "7. every claim ID tagged (in its chapter) as an empirical statement has
#      at least one row of type `empirical`."
#
# All 9 chapter files now exist, but per-claim empirical tagging in chapter
# prose is not machine-readable (it's free text like "**[implementado]**"),
# so this still cannot be implemented without a stricter markup convention
# for maturity/epistemic tags. Do not silently drop this requirement.

FUENTES_PATH = REPO_ROOT / "docs" / "web" / "FUENTES.md"


def _parse_claim_rows(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse every `| Claim ID | ... |` table occurrence in the file.

    Returns (rows, malformed_lines). Does NOT stop scanning after the first
    non-table line following a header: a future FUENTES.md may contain more
    than one `## Claims`-style table (e.g. if chapters are authored one at a
    time and each appends its own header+rows block), so every occurrence of
    the header is found and its rows parsed. A row whose cell count is not 4
    is not silently skipped — it is collected as malformed so a dedicated
    test can fail loudly on it instead of the row disappearing unnoticed.
    """
    rows: list[dict[str, str]] = []
    malformed: list[str] = []
    in_claims_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| Claim ID |"):
            in_claims_table = True
            continue
        if in_claims_table and stripped.startswith("| ---"):
            continue
        if in_claims_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) != 4:
                malformed.append(line)
                continue
            claim_id, tipo, anchor, source = cells
            if claim_id.startswith("_(") or not claim_id:
                continue
            rows.append(
                {"claim_id": claim_id, "tipo": tipo, "anchor": anchor, "source": source}
            )
        elif in_claims_table and not stripped.startswith("|"):
            # End of THIS table only — keep scanning the rest of the file
            # for further `| Claim ID |` header blocks.
            in_claims_table = False
    return rows, malformed


def _chapter_path(anchor: str) -> Path:
    chapter_num = anchor.split("#", 1)[0]
    matches = list((REPO_ROOT / "docs" / "web").glob(f"{chapter_num}-*.md"))
    assert len(matches) == 1, f"expected exactly one chapter file for {chapter_num}, found {matches}"
    return matches[0]


def _resolve_source(source: str) -> Path:
    """Split 'path::symbol' or 'path#anchor' into (path, extra)."""
    for sep in ("::", "#"):
        if sep in source:
            path_part, _extra = source.split(sep, 1)
            return REPO_ROOT / path_part
    return REPO_ROOT / source


@pytest.fixture(scope="module")
def claim_rows() -> list[dict[str, str]]:
    text = FUENTES_PATH.read_text(encoding="utf-8")
    rows, _malformed = _parse_claim_rows(text)
    return rows


@pytest.fixture(scope="module")
def malformed_claim_rows() -> list[str]:
    text = FUENTES_PATH.read_text(encoding="utf-8")
    _rows, malformed = _parse_claim_rows(text)
    return malformed


def test_no_malformed_claim_rows(malformed_claim_rows):
    assert not malformed_claim_rows, (
        "malformed claim row(s) in FUENTES.md (expected exactly 4 cells: "
        "Claim ID | Tipo | Chapter anchor | Source):\n"
        + "\n".join(malformed_claim_rows)
    )


def test_no_duplicate_claim_ids(claim_rows):
    ids = [row["claim_id"] for row in claim_rows]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate claim IDs in FUENTES.md: {duplicates}"


def test_every_row_has_a_valid_type(claim_rows):
    for row in claim_rows:
        assert row["tipo"] in VALID_TYPES, f"{row['claim_id']}: invalid tipo {row['tipo']!r}"


def test_no_source_resolves_under_internal(claim_rows):
    """Defensive check: `docs/_internal/` no longer exists in this repository
    (deleted; see docs/web/FUENTES.md), so this cannot currently fail against
    a real row. It stays as a guard against that path-shape being
    reintroduced as a citable source later.
    """
    for row in claim_rows:
        assert "docs/_internal" not in row["source"], (
            f"{row['claim_id']}: docs/_internal/ is never valid evidence"
        )


def test_chapter_anchor_exists_in_chapter_file(claim_rows):
    for row in claim_rows:
        chapter_file = _chapter_path(row["anchor"])
        anchor_id = row["anchor"].split("#", 1)[1]
        text = chapter_file.read_text(encoding="utf-8")
        assert f'<a id="{anchor_id}"></a>' in text, (
            f"{row['claim_id']}: anchor {anchor_id!r} not found as literal "
            f'<a id="..."> in {chapter_file.name}'
        )


def test_source_path_exists(claim_rows):
    for row in claim_rows:
        source_path = _resolve_source(row["source"])
        assert source_path.exists(), f"{row['claim_id']}: source path not found: {source_path}"


def test_declared_symbol_exists_in_source(claim_rows):
    for row in claim_rows:
        if "::" not in row["source"]:
            continue
        path_part, symbol = row["source"].split("::", 1)
        source_path = REPO_ROOT / path_part
        text = source_path.read_text(encoding="utf-8")
        pattern = rf"\b(def|class)\s+{re.escape(symbol)}\b"
        assert re.search(pattern, text), (
            f"{row['claim_id']}: symbol {symbol!r} not found in {source_path}"
        )


# Scope note: a `#anchor` fragment in the Source column is only valid when
# the cited source is itself another docs/web/ chapter — chapters carry
# explicit `<a id="...">` tags by this project's own convention (see
# FUENTES.md's "Claims" section intro). Canonical normative/design docs under
# docs/ do NOT carry explicit `<a id="...">` anchors (they rely on ordinary
# markdown headings); citing one of those must use a whole-file path with no
# `#anchor` fragment, naming the section in the claim text instead. No row
# currently exercises this path (the Claims table is empty), so this is
# scope documentation, not a behavior change.
def test_declared_markdown_anchor_exists_in_target(claim_rows):
    for row in claim_rows:
        if "#" not in row["source"] or "::" in row["source"]:
            continue
        path_part, anchor = row["source"].split("#", 1)
        target_path = REPO_ROOT / path_part
        text = target_path.read_text(encoding="utf-8")
        assert f'<a id="{anchor}"></a>' in text or f"id=\"{anchor}\"" in text, (
            f"{row['claim_id']}: markdown anchor {anchor!r} not found in {target_path}"
        )
