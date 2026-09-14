"""Passive instance registry: heartbeat identity for resident Symbionts on
this machine. Organism writes, Observatory only reads (CLAUDE.md: Observatory
remains passive)."""

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
    """Stable identity for a resident configuration -- never the raw path
    itself (spec: instance_id is a path hash, never exposes filesystem
    layout or usernames)."""
    digest = hashlib.sha256((_NAMESPACE + resolved_state_file_path).encode("utf-8")).hexdigest()
    return digest[:16]


def new_run_id() -> str:
    """Fresh every process start, even resuming the same --state-file."""
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
) -> None:
    record = {
        "instance_id": instance_id,
        "run_id": run_id,
        "pid": pid,
        "display_id": display_id,
        "started_at": started_at,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "topology_revision": topology_revision,
    }
    _atomic_write_json(Path(observatory_dir) / "instances" / f"{instance_id}.json", record)


def read_registry(observatory_dir: Path) -> list[dict[str, Any]]:
    instances_dir = Path(observatory_dir) / "instances"
    if not instances_dir.is_dir():
        return []
    records = []
    for path in sorted(instances_dir.glob("*.json")):
        if path.name.endswith(".topology.json"):
            continue  # topology files share this directory but aren't registry records
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def classify_liveness(
    record: dict[str, Any], *, now: datetime, heartbeat_interval_seconds: float, ttl_seconds: float = 600.0
) -> str:
    """pid is never the liveness authority (PIDs are reused) -- only the
    heartbeat timestamp decides alive/stale/expired (spec: Identity and
    discovery)."""
    try:
        last_heartbeat = datetime.fromisoformat(record["last_heartbeat"])
    except (KeyError, ValueError):
        return "expired"
    age = (now - last_heartbeat).total_seconds()
    if age <= 2 * heartbeat_interval_seconds:
        return "alive"
    if age <= ttl_seconds:
        return "stale"
    return "expired"
