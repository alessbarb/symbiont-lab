from __future__ import annotations

import hashlib
import json
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
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or not 16 <= max_records <= 8192
        ):
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

    def get(self, record_id: str) -> ExperienceRecord | None:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("record_id must be a non-empty string")
        for record in self._records:
            if record.record_id == record_id:
                return record
        return None

    def append(self, record: ExperienceRecord) -> ExperienceRecord | None:
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
        return evicted

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
    def restore(
        cls, payload: Mapping[str, object] | None, *, organism_id: str
    ) -> "ExperienceLedger":
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


class HistoricalExperienceArchive:
    """Deterministic bounded reservoir of exact historical causal records.

    The hot ExperienceLedger keeps recent chronology. This archive preserves a
    stable all-time sample of older exact causal evidence without fabricating
    records from compressed episodic memory. Selection is deterministic from
    immutable record content, making checkpoint/replay behavior reproducible.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        organism_id: str,
        *,
        max_records: int = 8192,
        max_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id or len(organism_id) > 128:
            raise ValueError("organism_id must be a bounded non-empty string")
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or not 128 <= max_records <= 65536
        ):
            raise ValueError("max_records must be within [128, 65536]")
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or not 256 * 1024 <= max_bytes <= 64 * 1024 * 1024
        ):
            raise ValueError("max_bytes must be within [256 KiB, 64 MiB]")
        self._organism_id = organism_id
        self._max_records = max_records
        self._max_bytes = max_bytes
        self._records: dict[str, ExperienceRecord] = {}
        self._priorities: dict[str, int] = {}
        self._record_bytes: dict[str, int] = {}
        self._payload_bytes = 0
        self._seen_count = 0

    @property
    def organism_id(self) -> str:
        return self._organism_id

    @property
    def max_records(self) -> int:
        return self._max_records

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    @property
    def payload_bytes(self) -> int:
        return self._payload_bytes

    @property
    def seen_count(self) -> int:
        return self._seen_count

    @property
    def records(self) -> tuple[ExperienceRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (record.tick_class, record.record_id),
            )
        )

    @staticmethod
    def _record_size(record: ExperienceRecord) -> int:
        return len(
            json.dumps(
                record.canonical_payload(),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )

    @staticmethod
    def _priority(record: ExperienceRecord) -> int:
        digest = hashlib.sha256(
            f"{record.record_id}:{record.content_hash}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:16], "big")

    def consider(self, record: ExperienceRecord) -> bool:
        if not isinstance(record, ExperienceRecord):
            raise ValueError("record must be an ExperienceRecord")
        if record.organism_id != self._organism_id:
            raise ValueError("experience record belongs to a different organism")
        if record.record_id in self._records:
            return False
        self._seen_count += 1
        priority = self._priority(record)
        record_bytes = self._record_size(record)
        self._records[record.record_id] = record
        self._priorities[record.record_id] = priority
        self._record_bytes[record.record_id] = record_bytes
        self._payload_bytes += record_bytes

        while len(self._records) > self._max_records or self._payload_bytes > self._max_bytes:
            worst_id, _ = max(
                self._priorities.items(),
                key=lambda item: (item[1], item[0]),
            )
            self._payload_bytes -= self._record_bytes.pop(worst_id)
            del self._records[worst_id]
            del self._priorities[worst_id]
        return record.record_id in self._records

    def sample(self, limit: int) -> tuple[ExperienceRecord, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if limit == 0:
            return ()
        selected_ids = [
            record_id
            for record_id, _ in sorted(
                self._priorities.items(),
                key=lambda item: (item[1], item[0]),
            )[:limit]
        ]
        return tuple(
            sorted(
                (self._records[record_id] for record_id in selected_ids),
                key=lambda record: (record.tick_class, record.record_id),
            )
        )

    def checkpoint(self) -> dict[str, object]:
        ordered = sorted(
            self._records.values(),
            key=lambda record: (self._priorities[record.record_id], record.record_id),
        )
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self._organism_id,
            "max_records": self._max_records,
            "max_bytes": self._max_bytes,
            "seen_count": self._seen_count,
            "records": [record.canonical_payload() for record in ordered],
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
        *,
        organism_id: str,
    ) -> "HistoricalExperienceArchive":
        if payload is None:
            return cls(organism_id)
        if (
            not isinstance(payload, Mapping)
            or payload.get("schema_version") != cls.SCHEMA_VERSION
            or payload.get("organism_id") != organism_id
        ):
            raise ValueError("invalid historical experience archive checkpoint")
        raw_max = payload.get("max_records", 8192)
        raw_max_bytes = payload.get("max_bytes", 8 * 1024 * 1024)
        raw_seen = payload.get("seen_count", 0)
        if (
            isinstance(raw_max, bool)
            or not isinstance(raw_max, int)
            or isinstance(raw_max_bytes, bool)
            or not isinstance(raw_max_bytes, int)
            or isinstance(raw_seen, bool)
            or not isinstance(raw_seen, int)
            or raw_seen < 0
        ):
            raise ValueError("invalid historical archive counters")
        archive = cls(
            organism_id,
            max_records=raw_max,
            max_bytes=raw_max_bytes,
        )
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list) or len(raw_records) > archive.max_records:
            raise ValueError("invalid historical archive records")
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise ValueError("historical archive record must be an object")
            record = ExperienceRecord.restore(raw)
            if record.organism_id != organism_id or record.record_id in archive._records:
                raise ValueError("invalid historical archive record identity")
            record_bytes = archive._record_size(record)
            archive._records[record.record_id] = record
            archive._priorities[record.record_id] = archive._priority(record)
            archive._record_bytes[record.record_id] = record_bytes
            archive._payload_bytes += record_bytes
        if archive._payload_bytes > archive._max_bytes:
            raise ValueError("historical archive exceeds byte budget")
        archive._seen_count = max(raw_seen, len(archive._records))
        return archive


__all__ = ["ExperienceLedger", "HistoricalExperienceArchive"]
