from __future__ import annotations

from .conftest import REPO_ROOT


def test_roadmap_keeps_only_active_state():
    text = (REPO_ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    for must_have in (
        "## 1. North star",
        "## 2. Permanent architectural invariants",
        "## 3. Lifecycle semantics",
        "## 4. Merge and decision policy",
        "## 5. Claim vocabulary",
        "## 6. Evidence levels",
        "## 10. Phase B — Embodied causal agency",
        "## 19. Phase C — Genotype to phenotype to physical consequence",
        "## 25. Phase F — Population, communication and culture",
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
