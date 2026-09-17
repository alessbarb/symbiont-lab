from __future__ import annotations

from collections import deque
from typing import Iterable, Mapping

from .experience import ExperienceRecord


class ExperienceLedger:
    """Bounded immutable episode ledger owned by one organism.

    Records are append-only by identity. When capacity is reached the oldest
    episode ages out; the ledger never rewrites an episode in place. Evidence
    correction is represented by a new record with its own epistemic state and
    provenance, preserving the history needed for scientific audit.
    """

    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, max_records: int = 2048) -> None:
        if not isinstance(organism_id, str) or not organism_id or len(organism_id) > 128:
            raise ValueError("organism_id must be a bounded non-empty string")
        if isinstance(max_records, bool) or not isinstance(max_records, int) or not 16 <= max_records <= 8192:
            raise ValueError("max_records must be within [16, 8192]")
        self._organism_id = organism_id
        self._max_records = max_records
        self._records: deque[ExperienceRecord] = deque(maxlen=max_records)
        self._record_ids: set[str] = set()

    @property
    def organism_id(self) -> str:
        return self._organism_id

    @property
    def max_records(self) -> int:
        return self._max_records

    @property
    def records(self) -> tuple[ExperienceRecord, ...]:
        return tuple(self._records)

    def append(self, record: ExperienceRecord) -> None:
        if not isinstance(record, ExperienceRecord):
            raise ValueError("record must be an ExperienceRecord")
        if record.organism_id != self._organism_id:
            raise ValueError("experience record belongs to a different organism")
        if record.record_id in self._record_ids:
            raise ValueError("experience record_id already exists")
        evicted = self._records[0] if len(self._records) == self._max_records else None
        self._records.append(record)
        self._record_ids.add(record.record_id)
        if evicted is not None:
            self._record_ids.discard(evicted.record_id)

    def extend(self, records: Iterable[ExperienceRecord]) -> None:
        for record in records:
            self.append(record)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self._organism_id,
            "max_records": self._max_records,
            "records": [record.canonical_payload() for record in self._records],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "ExperienceLedger":
        if payload is None:
            return cls(organism_id)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid experience ledger checkpoint")
        if payload.get("organism_id") != organism_id:
            raise ValueError("experience ledger organism mismatch")
        raw_max = payload.get("max_records", 2048)
        if isinstance(raw_max, bool) or not isinstance(raw_max, int):
            raise ValueError("invalid experience ledger capacity")
        ledger = cls(organism_id, max_records=raw_max)
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list) or len(raw_records) > ledger.max_records:
            raise ValueError("invalid experience ledger records")
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise ValueError("experience ledger record must be an object")
            ledger.append(ExperienceRecord.restore(raw))
        return ledger
