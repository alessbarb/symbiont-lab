"""Read-only adapter for Observatory registry, journals, topology and manifests."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def observatory_package_root() -> Path | None:
    try:
        import observatory  # type: ignore
    except ImportError:
        return None
    module_file = getattr(observatory, "__file__", None)
    return Path(module_file).resolve().parent if module_file else None


def valid_instance_id(value: str) -> bool:
    return len(value) == 16 and all(char in "0123456789abcdef" for char in value)


_MANIFEST_FIELDS = {
    "manifest_version",
    "organism_id",
    "instance_id",
    "run_id",
    "last_sequence",
    "tick",
    "topology_revision",
    "schema_version",
    "kernel_version",
    "checkpoint_sha256",
    "topology_sha256",
    "captured_at",
    "git_commit",
    "consistency",
}


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _registry_api():
    try:
        from observatory.registry import classify_liveness, read_registry  # type: ignore
    except ImportError:
        try:
            from registry import classify_liveness, read_registry  # type: ignore
        except ImportError:
            return None, None
    return classify_liveness, read_registry


def parse_journal_line(line: str, run_id: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(entry, dict):
        return None
    sequence = entry.get("sequence")
    if not isinstance(sequence, int) or sequence < 0 or isinstance(sequence, bool):
        return None
    if entry.get("run_id") != run_id or "snapshot" not in entry:
        return None
    return entry


def read_journal(
    journal_dir: Path,
    run_id: str,
    positions: dict[Path, int],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    segments = sorted(
        [
            *journal_dir.glob(f"{run_id}-*.ndjson"),
            *journal_dir.glob(f"{run_id}-*.ndjson.gz"),
        ]
    )
    live = set(segments)
    for stale in list(positions):
        if stale not in live:
            positions.pop(stale, None)

    for segment in segments:
        try:
            if segment.suffix == ".gz":
                previous = positions.get(segment, 0)
                index = -1
                with gzip.open(segment, "rt", encoding="utf-8") as handle:
                    for index, line in enumerate(handle):
                        if index < previous:
                            continue
                        entry = parse_journal_line(line, run_id)
                        if entry:
                            entries.append(entry)
                positions[segment] = index + 1
            else:
                previous = positions.get(segment, 0)
                with segment.open("rb") as handle:
                    handle.seek(previous)
                    data = handle.read()
                end = data.rfind(b"\n")
                if end < 0:
                    continue
                for line in data[: end + 1].decode("utf-8").splitlines():
                    entry = parse_journal_line(line, run_id)
                    if entry:
                        entries.append(entry)
                positions[segment] = previous + end + 1
        except OSError:
            continue
    return entries


class ObservatorySource:
    """Read-only access to one Observatory state directory."""

    def __init__(
        self,
        root: Path | None,
        *,
        heartbeat_interval_seconds: float | None = None,
    ) -> None:
        self.root = root
        if heartbeat_interval_seconds is None:
            try:
                from observatory.config import DEFAULT_HEARTBEAT_INTERVAL_SECONDS  # type: ignore
            except ImportError:
                try:
                    from config import DEFAULT_HEARTBEAT_INTERVAL_SECONDS  # type: ignore
                except ImportError:
                    heartbeat_interval_seconds = 15.0
                else:
                    heartbeat_interval_seconds = DEFAULT_HEARTBEAT_INTERVAL_SECONDS
            else:
                heartbeat_interval_seconds = DEFAULT_HEARTBEAT_INTERVAL_SECONDS
        self.heartbeat_interval_seconds = float(heartbeat_interval_seconds)

    @property
    def available(self) -> bool:
        _, read_registry = _registry_api()
        return self.root is not None and read_registry is not None

    def fleet_snapshot(self) -> list[dict[str, Any]]:
        classify_liveness, read_registry = _registry_api()
        if self.root is None or classify_liveness is None or read_registry is None:
            return []
        now = datetime.now(timezone.utc)
        instances = [
            {
                **record,
                "liveness": classify_liveness(
                    record,
                    now=now,
                    heartbeat_interval_seconds=self.heartbeat_interval_seconds,
                ),
            }
            for record in read_registry(self.root)
        ]
        return [instance for instance in instances if instance["liveness"] != "expired"]

    def instance_record(self, instance_id: str) -> dict[str, Any] | None:
        _, read_registry = _registry_api()
        if self.root is None or read_registry is None:
            return None
        records = {record["instance_id"]: record for record in read_registry(self.root)}
        return records.get(instance_id)

    def topology(self, instance_id: str) -> dict[str, Any] | None:
        if self.root is None:
            return None
        path = self.root / "instances" / f"{instance_id}.topology.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def journal_entries(
        self,
        run_id: str,
        positions: dict[Path, int],
    ) -> list[dict[str, Any]]:
        if self.root is None:
            return []
        journal_dir = self.root / "journal"
        if not journal_dir.exists():
            return []
        return read_journal(journal_dir, run_id, positions)

    def manifest(self, instance_id: str) -> dict[str, Any] | None:
        if self.root is None or not valid_instance_id(instance_id):
            return None
        evidence = _read_json_object(self.root / "manifests" / f"{instance_id}.manifest.json")
        if evidence is None or evidence.get("instance_id") != instance_id:
            return None
        projected = {key: value for key, value in evidence.items() if key in _MANIFEST_FIELDS}
        projected["projection"] = "observatory-provenance-v1"
        return projected

    def history_summary(self, instance_id: str) -> dict[str, Any] | None:
        record = self.instance_record(instance_id)
        if self.root is None or record is None:
            return None
        run_id = record.get("run_id")
        if not run_id:
            return None
        payload = _read_json_object(self.root / "summaries" / f"{run_id}.summary.json")
        if payload is None or payload.get("run_id") != run_id:
            return None
        return payload
