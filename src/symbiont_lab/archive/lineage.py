from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .studies import StudyArchive, StudyRecord


def trace_lineage(archive: StudyArchive, record_id: str) -> list[StudyRecord]:
    """Retrieve full ancestor lineage of a study record."""
    return archive.lineage(record_id)


def format_lineage_chain(records: list[StudyRecord]) -> str:
    """Format a chain of study records into a human-readable lineage string."""
    if not records:
        return "Empty lineage."
    parts = []
    for idx, record in enumerate(records):
        prefix = "└── " if idx == len(records) - 1 else "├── "
        parts.append(f"{prefix}[{record.record_id}] {record.created_at} (source: {record.source})")
    return "\n".join(parts)
