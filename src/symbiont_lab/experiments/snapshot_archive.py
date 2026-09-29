"""Immutable input snapshot capture for scientific and equivalence runs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
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


def _bundle_model_names(bundle: Path) -> tuple[str, ...]:
    try:
        with zipfile.ZipFile(bundle) as archive:
            return tuple(
                sorted(
                    name
                    for name in archive.namelist()
                    if name.startswith("models/") and not name.endswith("/")
                )
            )
    except (OSError, zipfile.BadZipFile):
        return ()


def _bundle_models_hash(bundle: Path) -> str:
    """Hash model artifacts embedded in the portable organism bundle."""
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(bundle) as archive:
            for name in _bundle_model_names(bundle):
                rel = name.removeprefix("models/").encode()
                payload = archive.read(name)
                digest.update(len(rel).to_bytes(4, "big"))
                digest.update(rel)
                digest.update(hashlib.sha256(payload).digest())
    except (OSError, zipfile.BadZipFile):
        return digest.hexdigest()
    return digest.hexdigest()


def _extract_bundle_models(bundle: Path, destination: Path) -> int:
    """Extract only embedded model artifacts, rejecting traversal/absolute paths."""
    names = _bundle_model_names(bundle)
    if not names:
        return 0
    count = 0
    with zipfile.ZipFile(bundle) as archive:
        for name in names:
            relative = PurePosixPath(name).relative_to("models")
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError(f"unsafe embedded model path: {name}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            count += 1
    return count


def inspect_snapshot_source(source: Path) -> dict[str, Any]:
    """Report whether a source directory is complete enough for immutable capture."""
    source = source.resolve()
    organism = source / "organism.symbiont"
    body = source / "body.json"
    models = source / "models"
    external_models = (
        tuple(sorted(path.relative_to(models).as_posix() for path in models.rglob("*") if path.is_file()))
        if models.is_dir()
        else ()
    )
    embedded_models = _bundle_model_names(organism) if organism.is_file() else ()
    return {
        "source": str(source),
        "organism_present": organism.is_file(),
        "body_present": body.is_file(),
        "external_model_count": len(external_models),
        "embedded_model_count": len(embedded_models),
        "model_source": (
            "external"
            if external_models
            else "bundle"
            if embedded_models
            else "none"
        ),
        "capturable": organism.is_file() and body.is_file(),
        **(_bundle_metadata(organism) if organism.is_file() else {}),
        **(_body_metadata(body) if body.is_file() else {}),
    }


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
                            "snapshot_schema": payload.get("runtime_schema_version")
                            or payload.get("schema_version"),
                            "body_kind_from_bundle": payload.get("body_kind"),
                            "body_age_ticks_from_bundle": payload.get("body_age_ticks"),
                            "embodiment_id_from_bundle": payload.get("embodiment_id"),
                            "body_id_from_bundle": payload.get("body_id"),
                            "checkpoint_id": payload.get("checkpoint_id"),
                            "checkpoint_hash": payload.get("checkpoint_hash"),
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
        models_source = "none"
        if models.is_dir() and any(path.is_file() for path in models.rglob("*")):
            shutil.copytree(models, tmp / "models")
            models_source = "external"
        else:
            (tmp / "models").mkdir()
            if _extract_bundle_models(organism, tmp / "models"):
                models_source = "bundle"

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
            "models_source": models_source,
            **_bundle_metadata(organism),
            **_body_metadata(body),
            "organism_sha256": _sha256(tmp / "organism.symbiont"),
            "body_sha256": _sha256(tmp / "body.json"),
            "bundle_models_tree_sha256": _bundle_models_hash(tmp / "organism.symbiont"),
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
        "bundle_models_tree_sha256": _bundle_models_hash(snapshot / "organism.symbiont"),
        "models_tree_sha256": _tree_hash(snapshot / "models"),
    }
    for key, value in checks.items():
        if manifest.get(key) != value:
            raise ValueError(f"snapshot integrity mismatch: {key}")
    source_commit = str(manifest.get("source_commit") or "")
    if len(source_commit) != 40 or any(
        ch not in "0123456789abcdef" for ch in source_commit.lower()
    ):
        raise ValueError("snapshot source_commit must be a full commit SHA")
    return manifest
