from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class LineageRecord:
    genome_id: str
    parent_ids: tuple[str, ...]
    genome_hash: str
    created_at_generation: int


class LineageArchive:
    def __init__(self) -> None:
        self._records: dict[str, LineageRecord] = {}

    def _would_create_cycle(self, genome_id: str, parent_ids: tuple[str, ...]) -> bool:
        stack = list(parent_ids)
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == genome_id:
                return True
            if current in seen or current not in self._records:
                continue
            seen.add(current)
            stack.extend(self._records[current].parent_ids)
        return False

    def record(self, entry: LineageRecord) -> None:
        if entry.genome_id in self._records:
            raise ValueError(f"genome_id {entry.genome_id!r} already recorded")
        missing_parents = [parent_id for parent_id in entry.parent_ids if parent_id not in self._records]
        if missing_parents:
            raise ValueError(f"parent id(s) not yet recorded: {missing_parents}")
        if self._would_create_cycle(entry.genome_id, entry.parent_ids):
            raise ValueError(f"recording {entry.genome_id!r} with parents {entry.parent_ids} would create a cycle")
        self._records[entry.genome_id] = entry

    def ancestors_of(self, genome_id: str) -> tuple[LineageRecord, ...]:
        result: list[LineageRecord] = []
        seen: set[str] = set()
        stack = list(self._records[genome_id].parent_ids) if genome_id in self._records else []
        while stack:
            current_id = stack.pop(0)
            if current_id in seen or current_id not in self._records:
                continue
            seen.add(current_id)
            record = self._records[current_id]
            result.append(record)
            stack.extend(record.parent_ids)
        return tuple(result)

    def export(self) -> tuple[dict[str, Any], ...]:
        return tuple(asdict(record) for record in self._records.values())

    @classmethod
    def restore(cls, payload: tuple[dict[str, Any], ...]) -> "LineageArchive":
        archive = cls()
        for entry in payload:
            archive.record(
                LineageRecord(
                    genome_id=entry["genome_id"],
                    parent_ids=tuple(entry["parent_ids"]),
                    genome_hash=entry["genome_hash"],
                    created_at_generation=entry["created_at_generation"],
                )
            )
        return archive
