from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_roadmap_keeps_only_active_state():
    text = (REPO_ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    for must_have in (
        "## North star",
        "## Permanent invariants",
        "## Birth, identity, dormancy and death",
        "## Merge policy",
        "## Decision gates",
        "## Milestone I — Fisiología integrada",
        "## Milestone J — Desarrollo predictivo",
        "## Milestone K — Sociabilidad emergente",
    ):
        assert must_have in text, f"missing from active roadmap.md: {must_have}"
    for must_not_have in (
        "## Milestone A — Safe real perception",
        "## Milestone F — Digital physiology",
        "## Milestone H — Digital ecology",
        "## Tracking",
        "### Completed development",
    ):
        assert must_not_have not in text, f"should have moved out: {must_not_have}"


def test_roadmap_log_has_full_history_verbatim():
    log_path = REPO_ROOT / "docs" / "history" / "roadmap-log.md"
    assert log_path.is_file(), f"Not found: {log_path}"
    text = log_path.read_text(encoding="utf-8")
    for must_have in (
        "## 2026-09-14 developmental restructures",
        "### Completed development",
        "## Milestone A — Safe real perception",
        "## Milestone H — Digital ecology",
        "## Tracking",
        # spot-check a specific, hard-to-fake historical entry survives verbatim:
        "v0.79.26 — K measurement refinement",
    ):
        assert must_have in text, f"missing from roadmap-log.md: {must_have}"
