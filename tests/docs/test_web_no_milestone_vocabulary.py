from __future__ import annotations

from .conftest import CHAPTERS, REPO_ROOT

# The two canonical design docs are genuinely named with "milestone" in their
# filename (milestone-j-desarrollo-predictivo.md and
# milestone-k-sociabilidad-emergente.md) — chapters 07 and 08 cite them both
# as backticked display text (docs/design/...) and as the relative link
# target (../design/...), so the bare filename is stripped regardless of
# which path prefix precedes it. That is a filename, not project-management
# framing in the prose, so it is removed before checking for the banned word
# elsewhere in each chapter.
_ALLOWED_FILENAME_MENTIONS = (
    "milestone-j-desarrollo-predictivo.md",
    "milestone-k-sociabilidad-emergente.md",
)


def _strip_allowed_mentions(text: str) -> str:
    for allowed in _ALLOWED_FILENAME_MENTIONS:
        text = text.replace(allowed, "")
    return text


def test_no_chapter_uses_milestone_vocabulary():
    offenders: list[str] = []
    for chapter in CHAPTERS:
        text = (REPO_ROOT / "docs" / "explanation" / "concepts" / chapter).read_text(encoding="utf-8")
        if "milestone" in _strip_allowed_mentions(text).lower():
            offenders.append(chapter)
    assert not offenders, f"project-management vocabulary found in: {offenders}"


def test_fuentes_claim_ids_avoid_milestone_vocabulary():
    text = (REPO_ROOT / "docs" / "explanation" / "concepts" / "SOURCES.md").read_text(encoding="utf-8")
    stripped = _strip_allowed_mentions(text)
    # Claim IDs are the one part of SOURCES.md that is our own naming choice
    # (unlike Source cells, which legitimately cite real canonical filenames)
    # — only the first pipe-delimited column of each Claims-table row.
    offenders = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip().startswith("|") and "milestone" in line.lower()
    ]
    assert not offenders, f"claim ID or row references milestone vocabulary: {offenders}"
