"""Exact event-stream codec for telemetry v4.1."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, TextIO

from .telemetry_compaction import canonical_json_bytes, payload_sha256
from .telemetry_schema import EVENT_RULES, TemporalClass, event_mode


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _is_prefix(prefix: list[Any], value: list[Any]) -> bool:
    return len(prefix) <= len(value) and all(
        _exact_equal(left, right) for left, right in zip(prefix, value)
    )


class EventStreamWriter:
    """Persist event snapshots according to explicit ephemeral/cumulative semantics."""

    def __init__(self, handle: TextIO) -> None:
        self.handle = handle
        self._previous_cumulative: dict[str, list[Any]] = {}
        self.records = 0
        self.bytes_written = 0

    def append(self, tick: int, channel: str, value: Any) -> list[str]:
        mode = event_mode(channel)
        hashes: list[str] = []
        if not isinstance(value, (list, tuple)):
            record = {
                "t": int(tick),
                "c": str(channel),
                "o": "snapshot",
                "v": deepcopy(value),
            }
            hashes.append(self._write(record))
            if mode is TemporalClass.EVENT_CUMULATIVE:
                self._previous_cumulative[channel] = []
            return hashes

        current = [deepcopy(item) for item in value]
        if mode is TemporalClass.EVENT_EPHEMERAL:
            if current:
                record = {
                    "t": int(tick),
                    "c": str(channel),
                    "o": "events",
                    "v": current,
                }
                hashes.append(self._write(record))
            return hashes

        if channel not in self._previous_cumulative:
            record = {
                "t": int(tick),
                "c": str(channel),
                "o": "reset",
                "v": current,
            }
            hashes.append(self._write(record))
            self._previous_cumulative[channel] = current
            return hashes

        previous = self._previous_cumulative[channel]
        if _is_prefix(previous, current):
            appended = current[len(previous) :]
            if appended:
                record = {
                    "t": int(tick),
                    "c": str(channel),
                    "o": "append_many",
                    "q": len(previous),
                    "v": appended,
                }
                hashes.append(self._write(record))
        else:
            record = {
                "t": int(tick),
                "c": str(channel),
                "o": "reset",
                "v": current,
            }
            hashes.append(self._write(record))
        self._previous_cumulative[channel] = current
        return hashes

    def drop(self, channel: str) -> None:
        self._previous_cumulative.pop(str(channel), None)

    def _write(self, record: Mapping[str, Any]) -> str:
        encoded = canonical_json_bytes(record)
        self.handle.write(encoded.decode("utf-8"))
        self.handle.write("\n")
        self.records += 1
        self.bytes_written += len(encoded) + 1
        return payload_sha256(record)


class EventStreamReader:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def prime(self, events: Mapping[str, Any]) -> None:
        for channel, value in events.items():
            self.values[str(channel)] = deepcopy(value)

    def begin_tick(self) -> None:
        for rule in EVENT_RULES:
            if rule.temporal_class is TemporalClass.EVENT_EPHEMERAL and rule.channel in self.values:
                self.values[rule.channel] = []

    def apply(self, record: Mapping[str, Any]) -> None:
        channel = str(record["c"])
        mode = event_mode(channel)
        operation = str(record["o"])
        value = deepcopy(record.get("v"))
        if operation == "snapshot":
            self.values[channel] = value
            return
        if operation == "reset":
            if not isinstance(value, list):
                raise ValueError("event reset payload must be a list")
            self.values[channel] = value
            return
        if operation == "events":
            if mode is not TemporalClass.EVENT_EPHEMERAL:
                raise ValueError("events operation used for cumulative channel")
            if not isinstance(value, list):
                raise ValueError("events payload must be a list")
            self.values[channel] = value
            return
        if operation == "event":
            if mode is not TemporalClass.EVENT_EPHEMERAL:
                raise ValueError("event operation used for cumulative channel")
            current = self.values.setdefault(channel, [])
            if not isinstance(current, list):
                raise ValueError("ephemeral event channel is not a list")
            expected = len(current)
            sequence = int(record.get("q", expected))
            if sequence != expected:
                raise ValueError("ephemeral event sequence gap")
            current.append(value)
            return
        if operation == "append_many":
            if mode is not TemporalClass.EVENT_CUMULATIVE:
                raise ValueError("append_many operation used for ephemeral channel")
            if not isinstance(value, list):
                raise ValueError("append_many payload must be a list")
            current = self.values.setdefault(channel, [])
            if not isinstance(current, list):
                raise ValueError("cumulative event channel is not a list")
            expected = len(current)
            sequence = int(record.get("q", expected))
            if sequence != expected:
                raise ValueError("cumulative event sequence gap")
            current.extend(value)
            return
        if operation == "append":
            if mode is not TemporalClass.EVENT_CUMULATIVE:
                raise ValueError("append operation used for ephemeral channel")
            current = self.values.setdefault(channel, [])
            if not isinstance(current, list):
                raise ValueError("cumulative event channel is not a list")
            expected = len(current)
            sequence = int(record.get("q", expected))
            if sequence != expected:
                raise ValueError("cumulative event sequence gap")
            current.append(value)
            return
        raise ValueError(f"unknown event operation: {operation!r}")

    def drop(self, channel: str) -> None:
        self.values.pop(str(channel), None)


def iter_event_records(path: str | Path):
    target = Path(path)
    if not target.is_file():
        return
    with target.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"invalid event record at line {line_no}")
            yield item


__all__ = [
    "EventStreamReader",
    "EventStreamWriter",
    "iter_event_records",
]
