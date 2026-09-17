# tests/docs/test_web_sources_exist.py
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FUENTES_PATH = REPO_ROOT / "docs" / "web" / "FUENTES.md"
VALID_TYPES = {"normative", "formal", "implementation", "empirical"}


def _parse_claim_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_claims_table = False
    for line in text.splitlines():
        if line.strip().startswith("| Claim ID |"):
            in_claims_table = True
            continue
        if in_claims_table and line.strip().startswith("| ---"):
            continue
        if in_claims_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 4:
                continue
            claim_id, tipo, anchor, source = cells
            if claim_id.startswith("_(") or not claim_id:
                continue
            rows.append(
                {"claim_id": claim_id, "tipo": tipo, "anchor": anchor, "source": source}
            )
        elif in_claims_table and not line.strip().startswith("|"):
            break
    return rows


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
    return _parse_claim_rows(text)


def test_no_duplicate_claim_ids(claim_rows):
    ids = [row["claim_id"] for row in claim_rows]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate claim IDs in FUENTES.md: {duplicates}"


def test_every_row_has_a_valid_type(claim_rows):
    for row in claim_rows:
        assert row["tipo"] in VALID_TYPES, f"{row['claim_id']}: invalid tipo {row['tipo']!r}"


def test_no_source_resolves_under_internal(claim_rows):
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
