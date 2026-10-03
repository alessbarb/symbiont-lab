"""Version-independent Physics3D telemetry readers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Protocol

from lab.physics3d.telemetry.v41 import TelemetryV41Reader


class TelemetryReaderProtocol(Protocol):
    root: Path

    def state_at(self, tick: int) -> dict[str, Any]: ...
    def summary_at(self, tick: int) -> dict[str, Any]: ...
    def iter_states(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]: ...
    def iter_summaries(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]: ...
    def iter_events(
        self,
        *,
        event_type: str | None = None,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]: ...


def _manifest_version(path: Path) -> str | None:
    manifest = path / "manifest.json"
    if not manifest.is_file():
        return None
    import json

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    value = payload.get("schema_version")
    return str(value) if value is not None else None


def detect_telemetry_run(path: str | Path) -> tuple[str, Path]:
    target = Path(path).expanduser()
    if target.is_file():
        return "legacy", target
    if not target.is_dir():
        raise FileNotFoundError(f"telemetry path not found: {target}")
    if (target / "ticks.ndjson").is_file():
        if _manifest_version(target) != "4.1":
            raise ValueError(f"unsupported telemetry format under {target}; only v4.1 is read")
        return "v4.1", target
    candidates = sorted(
        (child for child in target.iterdir() if (child / "ticks.ndjson").is_file()),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"telemetry run not found under: {target}")
    return detect_telemetry_run(candidates[0])


def open_telemetry(path: str | Path) -> TelemetryReaderProtocol:
    version, target = detect_telemetry_run(path)
    if version != "v4.1":
        raise ValueError(
            "single-file telemetry exposes summaries only; it has no reconstructible rich state"
        )
    return TelemetryV41Reader(target, verify=True)


__all__ = [
    "TelemetryReaderProtocol",
    "detect_telemetry_run",
    "open_telemetry",
]
