from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .experiment import ExperimentSpec
from .interpretation import StudyInterpretation
from .study import StudyResult


@dataclass(slots=True, frozen=True)
class StudyRecord:
    record_id: str
    created_at: str
    source: str
    parent_record_id: str | None
    base_spec: dict[str, object]
    study: dict[str, object]
    interpretation: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class StudyArchive:
    """Append-only observer memory for completed synthetic comparative studies.

    This archive is deliberately outside the simulated species. Agents, collective
    trust, reasoning, curiosity and metacognition never read it.
    """

    def __init__(self, path: str | Path = ".symbiont/studies.jsonl") -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(
        self,
        base_spec: ExperimentSpec,
        study: StudyResult,
        interpretation: StudyInterpretation,
        *,
        source: str,
        parent_record_id: str | None = None,
    ) -> StudyRecord:
        parent = str(parent_record_id).strip() if parent_record_id else None
        record = StudyRecord(
            record_id=uuid4().hex[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            parent_record_id=parent or None,
            base_spec=base_spec.as_dict(),
            study=study.as_dict(),
            interpretation=interpretation.as_dict(),
        )
        line = json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":"))
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return record

    def recent(self, limit: int = 20) -> list[StudyRecord]:
        if limit <= 0 or not self.path.exists():
            return []
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []

        records: list[StudyRecord] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                raw: dict[str, Any] = json.loads(line)
                records.append(
                    StudyRecord(
                        record_id=str(raw["record_id"]),
                        created_at=str(raw["created_at"]),
                        source=str(raw.get("source", "unknown")),
                        parent_record_id=(
                            str(raw["parent_record_id"])
                            if raw.get("parent_record_id")
                            else None
                        ),
                        base_spec=dict(raw.get("base_spec", {})),
                        study=dict(raw.get("study", {})),
                        interpretation=dict(raw.get("interpretation", {})),
                    )
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if len(records) >= limit:
                break
        return records

    def lineage(self, record_id: str, limit: int = 100) -> list[StudyRecord]:
        """Return a record and its known ancestors, newest to oldest."""
        records = self.recent(limit)
        by_id = {record.record_id: record for record in records}
        lineage: list[StudyRecord] = []
        current = by_id.get(record_id)
        seen: set[str] = set()
        while current is not None and current.record_id not in seen:
            lineage.append(current)
            seen.add(current.record_id)
            current = by_id.get(current.parent_record_id or "")
        return lineage
