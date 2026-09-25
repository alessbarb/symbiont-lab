"""Durable files for Physics3D apparatus state and passive telemetry."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

from .runtime import Tick3D
from .telemetry_reader import detect_telemetry_run, open_telemetry


def _atomic_write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
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


def save_symbiont_bundle(
    runtime_payload: dict,
    models_dir: str | Path,
    path: str | Path,
) -> Path:
    """Atomically save one portable organism bundle, including private SLM artifacts."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    models_root = Path(models_dir).expanduser()
    registry = runtime_payload.get("private_model_registry", {})
    records = registry.get("records", []) if isinstance(registry, dict) else []
    model_ids = [
        str(record.get("model_id"))
        for record in records
        if (
            isinstance(record, dict)
            and isinstance(record.get("model_id"), str)
            and record.get("state") != "retired"
        )
    ]

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    os.close(fd)
    try:
        with zipfile.ZipFile(
            temp_name,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "runtime.json",
                json.dumps(
                    runtime_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
            )
            for model_id in sorted(set(model_ids)):
                for suffix in (".json", ".pt", ".tokenizer.json"):
                    source = models_root / f"{model_id}{suffix}"
                    if source.is_file():
                        archive.write(
                            source,
                            arcname=f"models/{model_id}{suffix}",
                        )
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target


def read_symbiont_bundle_runtime(path: str | Path) -> dict:
    """Read only runtime.json from a portable organism bundle.

    Catalogs and preflight checks must not materialize private model artifacts.
    Full artifact extraction belongs exclusively to an actual runtime restore.
    """
    source = Path(path).expanduser()
    with zipfile.ZipFile(source, "r") as archive:
        try:
            raw = json.loads(archive.read("runtime.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError("portable Symbiont bundle has no runtime.json") from exc
        if not isinstance(raw, dict):
            raise ValueError("portable Symbiont runtime root must be an object")
        return raw


def load_symbiont_bundle(
    path: str | Path,
    models_dir: str | Path,
) -> dict:
    """Restore runtime state and materialize bundled private SLM artifacts."""
    source = Path(path).expanduser()
    models_root = Path(models_dir).expanduser()
    models_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        if "runtime.json" not in names:
            raise ValueError("portable Symbiont bundle has no runtime.json")
        raw = json.loads(archive.read("runtime.json").decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("portable Symbiont runtime root must be an object")

        for name in sorted(names):
            if not name.startswith("models/"):
                continue
            leaf = name.removeprefix("models/")
            if "/" in leaf or not leaf or not (leaf.endswith(".json") or leaf.endswith(".pt")):
                raise ValueError("portable Symbiont bundle contains unsafe model path")
            destination = models_root / leaf
            temporary = destination.with_name(f".{destination.name}.tmp")
            temporary.write_bytes(archive.read(name))
            os.replace(temporary, destination)
    return raw


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

    def __init__(self, path: str | Path, *, flush_every: int = 64) -> None:
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", buffering=8192)
        self._flush_every = int(flush_every)
        self._pending = 0

    def append(self, record: Tick3D) -> None:
        self._handle.write(
            json.dumps(
                asdict(record),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        self._handle.write("\n")
        self._pending += 1
        if self._pending >= self._flush_every:
            self._handle.flush()
            self._pending = 0

    def flush(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            self._pending = 0

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.flush()
            self._handle.close()
            self._pending = 0


def load_telemetry_records(
    path: str | Path,
    *,
    ignore_errors: bool = False,
) -> list[dict]:
    """Read Tick3D summaries through the version-neutral telemetry API."""
    version, target = detect_telemetry_run(path)
    if version != "legacy":
        return list(open_telemetry(target).iter_summaries())

    records = []
    with target.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except json.JSONDecodeError as exc:
                if ignore_errors:
                    continue
                raise ValueError(f"corrupt telemetry record at line {line_no}: {exc}") from exc
    return records


def load_telemetry_transitions(path: str | Path) -> list[dict]:
    """Read fully reconstructed rich states independent of storage version."""
    version, target = detect_telemetry_run(path)
    if version == "legacy":
        raise ValueError("historical single-file telemetry has no reconstructible rich transitions")
    return list(open_telemetry(target).iter_states())


__all__ = [
    "TelemetryWriter",
    "load_body_state_file",
    "load_runtime_state_file",
    "read_symbiont_bundle_runtime",
    "load_symbiont_bundle",
    "load_telemetry_records",
    "load_telemetry_transitions",
    "open_telemetry",
    "save_body_state_file",
    "save_runtime_state_file",
    "save_symbiont_bundle",
]
