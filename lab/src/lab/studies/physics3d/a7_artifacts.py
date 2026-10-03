"""Immutable artifact and same-host replay helpers for A7 run records."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REQUIRED_FILES = ("ticks.jsonl", "checkpoints.json", "validation.json")


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    return value


def write_execution_artifacts(
    destination: Path,
    *,
    manifest: Mapping[str, Any],
    ticks: Sequence[Mapping[str, Any]],
    checkpoints: Sequence[Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    """Write a complete, content-hashed execution directory without overwrite."""
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"A7 execution artifacts are immutable: {destination}")
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=parent))
    try:
        (staging / "ticks.jsonl").write_bytes(b"".join(_json_bytes(tick) for tick in ticks))
        (staging / "checkpoints.json").write_bytes(_json_bytes(list(checkpoints)))
        (staging / "validation.json").write_bytes(_json_bytes(dict(validation)))
        artifact_hashes = {
            name: hashlib.sha256((staging / name).read_bytes()).hexdigest()
            for name in _REQUIRED_FILES
        }
        final_manifest = dict(manifest)
        final_manifest["artifact_sha256"] = artifact_hashes
        (staging / "manifest.json").write_bytes(_json_bytes(final_manifest))
        for file in staging.iterdir():
            with file.open("rb") as stream:
                os.fsync(stream.fileno())
        directory_fd = os.open(staging, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return final_manifest


def verify_execution_artifacts(directory: Path) -> dict[str, Any]:
    """Verify presence and hashes; incomplete artifacts are never a pass."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return {"integrity": False, "outcome": "inconclusive", "reason": "missing manifest"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest["artifact_sha256"]
        if not isinstance(expected, dict):
            raise ValueError("artifact_sha256 must be an object")
        for name in _REQUIRED_FILES:
            file = directory / name
            if not file.is_file():
                raise FileNotFoundError(name)
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if expected.get(name) != actual:
                raise ValueError(f"hash mismatch: {name}")
        return {"integrity": True, "outcome": "verified", "artifact_count": len(_REQUIRED_FILES)}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"integrity": False, "outcome": "inconclusive", "reason": str(exc)}


def _contact_key(contact: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        contact.get("body_a"),
        contact.get("link_a"),
        contact.get("body_b"),
        contact.get("link_b"),
        json.dumps(contact.get("position_a", ()), sort_keys=True, separators=(",", ":")),
        json.dumps(contact.get("position_b", ()), sort_keys=True, separators=(",", ":")),
    )


def canonicalize_contacts(value: Any) -> Any:
    """Sort contact arrays by stable identifiers/coordinates recursively."""
    if isinstance(value, Mapping):
        return {
            key: canonicalize_contacts(item)
            if key != "contacts"
            else sorted((canonicalize_contacts(contact) for contact in item), key=_contact_key)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [canonicalize_contacts(item) for item in value]
    return value


def compare_replays(left: Any, right: Any, *, tolerance: float = 1e-9) -> dict[str, Any]:
    """Compare matched replay payloads, requiring exact discrete state equality."""
    if tolerance < 0 or not math.isfinite(tolerance):
        raise ValueError("tolerance must be finite and non-negative")
    left, right = canonicalize_contacts(left), canonicalize_contacts(right)
    maximum = 0.0
    differences: list[dict[str, Any]] = []

    def walk(a: Any, b: Any, path: str) -> None:
        nonlocal maximum
        markers = {"NaN", "Infinity", "-Infinity"}
        if (isinstance(a, str) and a in markers) or (isinstance(b, str) and b in markers):
            differences.append({"path": path, "kind": "non_finite"})
            return
        if isinstance(a, bool) or isinstance(b, bool):
            if type(a) is not type(b) or a != b:
                differences.append({"path": path, "kind": "discrete", "left": a, "right": b})
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isfinite(float(a)) or not math.isfinite(float(b)):
                differences.append({"path": path, "kind": "non_finite"})
            else:
                delta = abs(float(a) - float(b))
                maximum = max(maximum, delta)
                if delta > tolerance:
                    differences.append(
                        {"path": path, "kind": "numeric", "absolute_difference": delta}
                    )
        elif isinstance(a, Mapping) and isinstance(b, Mapping):
            if set(a) != set(b):
                differences.append({"path": path, "kind": "keys"})
                return
            for key in sorted(a):
                walk(a[key], b[key], f"{path}.{key}" if path else str(key))
        elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) != len(b):
                differences.append({"path": path, "kind": "length"})
                return
            for index, (left_item, right_item) in enumerate(zip(a, b, strict=True)):
                walk(left_item, right_item, f"{path}[{index}]")
        elif type(a) is not type(b) or a != b:
            differences.append({"path": path, "kind": "discrete", "left": a, "right": b})

    walk(left, right, "")
    return {
        "pass": not differences,
        "tolerance": tolerance,
        "maximum_absolute_difference": maximum,
        "differences": differences,
    }
