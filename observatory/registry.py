"""Passive instance registry: heartbeat identity for resident Symbionts on
this machine. Organism writes, Observatory only reads.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_NAMESPACE = "symbiont-observatory-instance"


def derive_instance_id(resolved_state_file_path: str) -> str:
    digest = hashlib.sha256((_NAMESPACE + resolved_state_file_path).encode("utf-8")).hexdigest()
    return digest[:16]


def new_run_id() -> str:
    return str(uuid.uuid4())


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_heartbeat(
    observatory_dir: Path,
    *,
    instance_id: str,
    run_id: str,
    pid: int,
    display_id: str,
    started_at: str,
    topology_revision: int,
    organism_id: str | None = None,
) -> None:
    record: dict[str, Any] = {
        "instance_id": instance_id,
        "run_id": run_id,
        "pid": pid,
        "display_id": display_id,
        "started_at": started_at,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "topology_revision": topology_revision,
    }
    if organism_id is not None:
        record["organism_id"] = organism_id
    _atomic_write_json(Path(observatory_dir) / "instances" / f"{instance_id}.json", record)


def _aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _valid_registry_record(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    instance_id = record.get("instance_id")
    run_id = record.get("run_id")
    pid = record.get("pid")
    display_id = record.get("display_id")
    revision = record.get("topology_revision")
    if (
        not isinstance(instance_id, str)
        or len(instance_id) != 16
        or any(char not in "0123456789abcdef" for char in instance_id)
    ):
        return False
    if not isinstance(run_id, str) or not run_id:
        return False
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 0:
        return False
    if not isinstance(display_id, str) or not display_id:
        return False
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        return False
    if _aware_datetime(record.get("started_at")) is None:
        return False
    if _aware_datetime(record.get("last_heartbeat")) is None:
        return False
    return True


def read_registry(observatory_dir: Path) -> list[dict[str, Any]]:
    instances_dir = Path(observatory_dir) / "instances"
    if not instances_dir.is_dir():
        return []
    records = []
    for path in sorted(instances_dir.glob("*.json")):
        if path.name.endswith(".topology.json"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if _valid_registry_record(record):
            records.append(record)
    return records


def classify_liveness(
    record: dict[str, Any],
    *,
    now: datetime,
    heartbeat_interval_seconds: float,
    ttl_seconds: float = 600.0,
) -> str:
    """Heartbeat timestamp is authoritative; malformed/future records expire."""
    last_heartbeat = _aware_datetime(record.get("last_heartbeat"))
    if last_heartbeat is None or now.tzinfo is None or now.utcoffset() is None:
        return "expired"
    try:
        age = (now - last_heartbeat).total_seconds()
    except TypeError:
        return "expired"
    if age < -2 * heartbeat_interval_seconds:
        return "expired"
    if age <= 2 * heartbeat_interval_seconds:
        return "alive"
    if age <= ttl_seconds:
        return "stale"
    return "expired"
