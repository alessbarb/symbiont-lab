"""Durable files for Physics3D apparatus state and passive telemetry."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
import tempfile
from typing import Iterable

from .runtime import Tick3D


def _atomic_write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def save_runtime_state_file(payload: dict, path: str | Path) -> Path:
    """Save the canonical body-independent organism runtime checkpoint."""
    return _atomic_write_json(Path(path).expanduser(), payload)


def load_runtime_state_file(path: str | Path) -> dict:
    target = Path(path).expanduser()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("organism runtime state root must be an object")
    return payload


def save_body_state_file(payload: dict, path: str | Path) -> Path:
    """Save apparatus-owned physical pose separately from the Symbiont file."""
    return _atomic_write_json(Path(path).expanduser(), payload)


def load_body_state_file(path: str | Path) -> dict:
    target = Path(path).expanduser()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("physical body state root must be an object")
    return payload


class TelemetryWriter:
    """Append-only apparatus telemetry. It never feeds cognition."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Tick3D) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    asdict(record),
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            )
            handle.write("\n")


__all__ = [
    "TelemetryWriter",
    "load_body_state_file",
    "load_runtime_state_file",
    "save_body_state_file",
    "save_runtime_state_file",
]
