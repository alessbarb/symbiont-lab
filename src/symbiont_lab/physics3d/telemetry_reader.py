"""Version-independent Physics3D telemetry readers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Protocol

from .telemetry import iter_v3_envelopes
from .telemetry_v4 import TelemetryV4Reader
from .telemetry_v41 import TelemetryV41Reader


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


class _V3Reader:
    def __init__(self, root: Path) -> None:
        self.root = root

    def iter_records(self, *, start_tick=None, end_tick=None):
        for envelope in iter_v3_envelopes(self.root, verify=True):
            payload = envelope.get("payload", {})
            if not isinstance(payload, dict):
                continue
            state = payload.get("transition", {})
            summary = payload.get("summary", {})
            if not isinstance(state, dict) or not isinstance(summary, dict):
                continue
            tick = int(state.get("tick", summary.get("tick", -1)))
            if start_tick is not None and tick < int(start_tick):
                continue
            if end_tick is not None and tick > int(end_tick):
                break
            yield dict(state), dict(summary)

    def iter_states(self, *, start_tick=None, end_tick=None):
        for state, _summary in self.iter_records(
            start_tick=start_tick,
            end_tick=end_tick,
        ):
            yield state

    def iter_summaries(self, *, start_tick=None, end_tick=None):
        for _state, summary in self.iter_records(
            start_tick=start_tick,
            end_tick=end_tick,
        ):
            yield summary

    def state_at(self, tick: int):
        requested = int(tick)
        for state, _summary in self.iter_records(
            start_tick=requested,
            end_tick=requested,
        ):
            return state
        raise KeyError(f"telemetry tick not found: {requested}")

    def summary_at(self, tick: int):
        requested = int(tick)
        for _state, summary in self.iter_records(
            start_tick=requested,
            end_tick=requested,
        ):
            return summary
        raise KeyError(f"telemetry tick not found: {requested}")

    def iter_events(self, *, event_type=None, start_tick=None, end_tick=None):
        for state in self.iter_states(start_tick=start_tick, end_tick=end_tick):
            tick = int(state.get("tick", -1))
            candidates = {
                "runtime.knowledge_events": (
                    state.get("runtime", {}) or {}
                ).get("knowledge_events", []),
                "runtime.runtime_events": (
                    state.get("runtime", {}) or {}
                ).get("runtime_events", []),
                "runtime.experience_records_created": (
                    state.get("runtime", {}) or {}
                ).get("experience_records_created", []),
                "cognition.mutations": (
                    state.get("cognition", {}) or {}
                ).get("mutations", []),
                "cognition.recycling_events": (
                    state.get("cognition", {}) or {}
                ).get("recycling_events", []),
                "sensorimotor.episodes": (
                    state.get("sensorimotor", {}) or {}
                ).get("episodes", []),
            }
            for channel, values in candidates.items():
                if event_type is not None and channel != event_type:
                    continue
                if isinstance(values, list):
                    for value in values:
                        yield {
                            "tick": tick,
                            "type": channel,
                            "operation": "snapshot",
                            "payload": value,
                        }


class _V4ReaderAdapter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._reader = TelemetryV4Reader(root, verify=True)

    def state_at(self, tick: int):
        return self._reader.state_at(tick)

    def summary_at(self, tick: int):
        requested = int(tick)
        for summary in self.iter_summaries(
            start_tick=requested,
            end_tick=requested,
        ):
            return summary
        raise KeyError(f"telemetry tick not found: {requested}")

    def iter_states(self, *, start_tick=None, end_tick=None):
        yield from self._reader.iter_states(
            start_tick=start_tick,
            end_tick=end_tick,
        )

    def iter_summaries(self, *, start_tick=None, end_tick=None):
        yield from self._reader.iter_summaries(
            start_tick=start_tick,
            end_tick=end_tick,
        )

    def iter_events(self, *, event_type=None, start_tick=None, end_tick=None):
        # Same logical fallback as v3; v4.0 predates the physical event stream.
        legacy = _LogicalEventProjection(self)
        yield from legacy.iter_events(
            event_type=event_type,
            start_tick=start_tick,
            end_tick=end_tick,
        )


class _LogicalEventProjection:
    def __init__(self, reader) -> None:
        self.reader = reader

    def iter_events(self, *, event_type=None, start_tick=None, end_tick=None):
        for state in self.reader.iter_states(
            start_tick=start_tick,
            end_tick=end_tick,
        ):
            tick = int(state.get("tick", -1))
            runtime = state.get("runtime", {}) or {}
            cognition = state.get("cognition", {}) or {}
            sensorimotor = state.get("sensorimotor", {}) or {}
            candidates = {
                "runtime.knowledge_events": runtime.get("knowledge_events", []),
                "runtime.runtime_events": runtime.get("runtime_events", []),
                "runtime.experience_records_created": runtime.get(
                    "experience_records_created", []
                ),
                "cognition.mutations": cognition.get("mutations", []),
                "cognition.recycling_events": cognition.get(
                    "recycling_events", []
                ),
                "sensorimotor.episodes": sensorimotor.get("episodes", []),
            }
            for channel, values in candidates.items():
                if event_type is not None and channel != event_type:
                    continue
                if isinstance(values, list):
                    for value in values:
                        yield {
                            "tick": tick,
                            "type": channel,
                            "operation": "snapshot",
                            "payload": value,
                        }


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
    if target.is_dir():
        if (target / "transitions.ndjson").is_file():
            return "v4.0", target
        if (target / "ticks.ndjson").is_file():
            if _manifest_version(target) == "4.1":
                return "v4.1", target
            return "v3", target
        candidates = sorted(
            (
                child
                for child in target.iterdir()
                if child.is_dir()
                and (
                    (child / "transitions.ndjson").is_file()
                    or (child / "ticks.ndjson").is_file()
                )
            ),
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"telemetry run not found under: {target}")
        return detect_telemetry_run(candidates[0])
    if target.is_file():
        return "legacy", target
    raise FileNotFoundError(f"telemetry path not found: {target}")


def open_telemetry(path: str | Path) -> TelemetryReaderProtocol:
    version, target = detect_telemetry_run(path)
    if version == "v4.1":
        return TelemetryV41Reader(target, verify=True)
    if version == "v4.0":
        return _V4ReaderAdapter(target)
    if version == "v3":
        return _V3Reader(target)
    raise ValueError(
        "historical single-file telemetry exposes summaries only; "
        "it has no reconstructible rich state"
    )


__all__ = [
    "TelemetryReaderProtocol",
    "detect_telemetry_run",
    "open_telemetry",
]
