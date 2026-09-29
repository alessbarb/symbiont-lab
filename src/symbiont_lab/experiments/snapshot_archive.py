"""Immutable input snapshot capture for scientific and equivalence runs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
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

        manifest = {
            "schema_version": 1,
            "snapshot_id": destination.name,
            "source_commit": source_commit,
            "body_kind": body_kind,
            "scenario": scenario,
            **_bundle_metadata(organism),
            "organism_sha256": _sha256(tmp / "organism.symbiont"),
            "body_sha256": _sha256(tmp / "body.json"),
            "models_tree_sha256": _tree_hash(tmp / "models"),
        }
        (tmp / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        verify_snapshot(tmp)
        for path in sorted(tmp.rglob("*"), reverse=True):
            if path.is_file():
                try:
                    path.chmod(0o444)
                except OSError:
                    pass
        os.replace(tmp, destination)
        return manifest
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def verify_snapshot(snapshot: Path) -> dict[str, Any]:
    manifest_path = snapshot / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("snapshot manifest.json missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "organism_sha256": _sha256(snapshot / "organism.symbiont"),
        "body_sha256": _sha256(snapshot / "body.json"),
        "models_tree_sha256": _tree_hash(snapshot / "models"),
    }
    for key, value in checks.items():
        if manifest.get(key) != value:
            raise ValueError(f"snapshot integrity mismatch: {key}")
    return manifest
