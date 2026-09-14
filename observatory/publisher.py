"""Fan-out publishing so every Observatory transport sees the identical
projected snapshot. ReplayRecorder is deliberately not a per-envelope sink:
write_replay() was never append-oriented -- it writes the whole bounded
collection atomically in one shot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

try:
    from .adapter import write_replay
    from .journal import Journal
except ImportError:  # resident.py runs this module bare-script style (cwd=observatory/)
    from adapter import write_replay
    from journal import Journal


class Sink(Protocol):
    def write(self, envelope: dict[str, Any]) -> None: ...


class StdoutSink:
    def write(self, envelope: dict[str, Any]) -> None:
        print(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")), flush=True)


class JournalSink:
    def __init__(self, observatory_dir: Path, *, run_id: str) -> None:
        self._journal = Journal(observatory_dir, run_id=run_id)

    def write(self, envelope: dict[str, Any]) -> None:
        self._journal.append(envelope)


class ReplayRecorder:
    def __init__(self) -> None:
        self._snapshots: list[dict[str, Any]] = []

    def record(self, snapshot: dict[str, Any]) -> None:
        self._snapshots.append(snapshot)

    def flush(self, path: Path) -> None:
        write_replay(path, self._snapshots)


class SnapshotPublisher:
    def __init__(self, sinks: list[Sink], *, replay_recorder: ReplayRecorder | None = None) -> None:
        self._sinks = sinks
        self._replay_recorder = replay_recorder

    def publish(self, envelope: dict[str, Any], snapshot: dict[str, Any]) -> None:
        for sink in self._sinks:
            sink.write(envelope)
        if self._replay_recorder is not None:
            self._replay_recorder.record(snapshot)
