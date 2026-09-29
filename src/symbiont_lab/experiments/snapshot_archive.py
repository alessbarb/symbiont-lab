"""Immutable input snapshot capture for scientific and equivalence runs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode()
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _body_metadata(body: Path) -> dict[str, Any]:
    try:
        payload = json.loads(body.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        "embodiment_id": payload.get("embodiment_id") or payload.get("epoch_id"),
        "body_kind_from_state": payload.get("body_kind") or payload.get("kind"),
        "body_age_ticks": payload.get("age_ticks") or payload.get("tick"),
    }


def _bundle_metadata(bundle: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(bundle) as archive:
            for name in ("manifest.json", "runtime.json"):
                if name in archive.namelist():
                    payload = json.loads(archive.read(name))
                    if isinstance(payload, dict):
                        return {
                            "organism_id": payload.get("organism_id"),
                            "captured_tick": payload.get("saved_at_tick") or payload.get("tick"),
                            "snapshot_schema": payload.get("schema_version"),
                        }
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError):
        pass
    return {}


def archive_snapshot(
    *,
    source: Path,
    destination: Path,
    source_commit: str,
    body_kind: str | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    destination = destination.resolve()
    organism = source / "organism.symbiont"
    body = source / "body.json"
    models = source / "models"
    if not organism.is_file() or not body.is_file():
        raise ValueError("snapshot source must contain organism.symbiont and body.json")
    if destination.exists():
        raise FileExistsError(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        shutil.copy2(organism, tmp / organism.name)
        shutil.copy2(body, tmp / body.name)
        if models.is_dir():
            shutil.copytree(models, tmp / "models")
        else:
            (tmp / "models").mkdir()

        for path in (tmp / "organism.symbiont", tmp / "body.json"):
            _fsync_file(path)
        for path in sorted((tmp / "models").rglob("*")):
            if path.is_file():
                _fsync_file(path)

        manifest = {
            "schema_version": 2,
            "snapshot_id": destination.name,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source_commit": source_commit,
            "body_kind": body_kind,
            "scenario": scenario,
            **_bundle_metadata(organism),
            **_body_metadata(body),
            "organism_sha256": _sha256(tmp / "organism.symbiont"),
            "body_sha256": _sha256(tmp / "body.json"),
            "models_tree_sha256": _tree_hash(tmp / "models"),
        }
        manifest_path = tmp / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        verify_snapshot(tmp)
        _fsync_dir(tmp / "models")
        _fsync_dir(tmp)
        os.replace(tmp, destination)
        _fsync_dir(destination.parent)

        for path in sorted(destination.rglob("*"), reverse=True):
            if path.is_file():
                try:
                    path.chmod(0o444)
                except OSError:
                    pass
        return manifest
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def verify_snapshot(snapshot: Path) -> dict[str, Any]:
    manifest_path = snapshot / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("snapshot manifest.json missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("snapshot manifest.json is invalid") from exc
    if not isinstance(manifest, dict):
        raise ValueError("snapshot manifest must be an object")
    if manifest.get("snapshot_id") != snapshot.name:
        raise ValueError("snapshot_id does not match directory name")
    for required in ("organism.symbiont", "body.json"):
        if not (snapshot / required).is_file():
            raise ValueError(f"snapshot is missing {required}")
    checks = {
        "organism_sha256": _sha256(snapshot / "organism.symbiont"),
        "body_sha256": _sha256(snapshot / "body.json"),
        "models_tree_sha256": _tree_hash(snapshot / "models"),
    }
    for key, value in checks.items():
        if manifest.get(key) != value:
            raise ValueError(f"snapshot integrity mismatch: {key}")
    return manifest
