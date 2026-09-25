"""Coherent capture manifest and export barrier for resident Symbiont instances.

Links durable organism_id, instance_id, run_id, confirmed journal sequence,
tick, topology revision, effective configuration, and artifact SHA256 hashes
into an atomically published manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _file_sha256(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _git_commit_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        return out if out else "unknown"
    except Exception:
        return "unknown"


@dataclass(slots=True, frozen=True)
class CaptureManifest:
    organism_id: str
    instance_id: str
    run_id: str
    last_sequence: int
    tick: int
    topology_revision: int
    schema_version: int
    kernel_version: str
    checkpoint_file: str
    checkpoint_sha256: str | None
    topology_file: str
    topology_sha256: str | None
    effective_config: dict[str, Any]
    captured_at: str
    git_commit: str = field(default_factory=_git_commit_sha)
    manifest_version: int = 1
    consistency: str = "atomic"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_capture_manifest(
    *,
    organism_id: str,
    instance_id: str,
    run_id: str,
    last_sequence: int,
    tick: int,
    topology_revision: int,
    schema_version: int,
    kernel_version: str,
    checkpoint_path: Path | str,
    topology_path: Path | str,
    effective_config: dict[str, Any],
    consistency: str = "atomic",
) -> CaptureManifest:
    ckpt_p = Path(checkpoint_path)
    topo_p = Path(topology_path)
    return CaptureManifest(
        organism_id=organism_id,
        instance_id=instance_id,
        run_id=run_id,
        last_sequence=last_sequence,
        tick=tick,
        topology_revision=topology_revision,
        schema_version=schema_version,
        kernel_version=kernel_version,
        checkpoint_file=ckpt_p.name,
        checkpoint_sha256=_file_sha256(ckpt_p),
        topology_file=topo_p.name,
        topology_sha256=_file_sha256(topo_p),
        effective_config=effective_config,
        captured_at=datetime.now(timezone.utc).isoformat(),
        consistency=consistency,
    )


def write_capture_manifest(target_path: Path | str, manifest: CaptureManifest) -> Path:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.as_dict()
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return target


def verify_capture_manifest(
    manifest_path: Path | str,
    *,
    base_dir: Path | str | None = None,
    checkpoint_path: Path | str | None = None,
    topology_path: Path | str | None = None,
) -> tuple[bool, list[str]]:
    path = Path(manifest_path)
    if not path.is_file():
        return False, [f"Manifest file not found: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Malformed JSON in manifest: {exc}"]

    required_fields = (
        "organism_id",
        "instance_id",
        "run_id",
        "last_sequence",
        "tick",
        "topology_revision",
        "checkpoint_file",
        "checkpoint_sha256",
        "topology_file",
        "topology_sha256",
        "effective_config",
    )
    errors: list[str] = []
    for f in required_fields:
        if f not in data:
            errors.append(f"Missing required manifest field: {f}")

    if errors:
        return False, errors

    search_dir = Path(base_dir) if base_dir is not None else path.parent
    if checkpoint_path is not None:
        ckpt_p = Path(checkpoint_path)
    else:
        for candidate in (
            search_dir / str(data["checkpoint_file"]),
            search_dir.parent / str(data["checkpoint_file"]),
            search_dir.parent.parent / str(data["checkpoint_file"]),
        ):
            if candidate.is_file():
                ckpt_p = candidate
                break
        else:
            ckpt_p = search_dir / str(data["checkpoint_file"])

    if ckpt_p.is_file():
        actual_hash = _file_sha256(ckpt_p)
        expected_hash = data.get("checkpoint_sha256")
        if expected_hash and actual_hash != expected_hash:
            errors.append(
                f"Checkpoint SHA256 mismatch (eventual/in-flight copy detected): "
                f"expected {expected_hash}, got {actual_hash}"
            )
    elif data.get("checkpoint_sha256") is not None:
        errors.append(f"Referenced checkpoint file not found: {data['checkpoint_file']}")

    if topology_path is not None:
        topo_p = Path(topology_path)
    else:
        for candidate in (
            search_dir / str(data["topology_file"]),
            search_dir / "instances" / str(data["topology_file"]),
            search_dir.parent / "instances" / str(data["topology_file"]),
            search_dir.parent / str(data["topology_file"]),
        ):
            if candidate.is_file():
                topo_p = candidate
                break
        else:
            topo_p = search_dir / str(data["topology_file"])

    if topo_p.is_file():
        actual_topo = _file_sha256(topo_p)
        expected_topo = data.get("topology_sha256")
        if expected_topo and actual_topo != expected_topo:
            errors.append(f"Topology SHA256 mismatch: expected {expected_topo}, got {actual_topo}")
    elif data.get("topology_sha256") is not None:
        errors.append(f"Referenced topology file not found: {data['topology_file']}")

    return len(errors) == 0, errors
