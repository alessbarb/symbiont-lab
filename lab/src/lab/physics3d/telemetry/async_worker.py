"""Shared bounded-worker lifecycle for versioned Physics3D telemetry writers."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any, Mapping, cast


class AsyncTelemetryWorker:
    """Serialize writer calls through a bounded FIFO without owning tick policy."""

    _STOP = object()

    def __init__(self, writer: Any, *, queue_size: int, thread_name: str) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._writer = writer
        self._snapshot_interval = writer._snapshot_interval
        self._queue: queue.Queue[object] = queue.Queue(maxsize=int(queue_size))
        self._submitted = 0
        self._closed = False
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=thread_name,
            daemon=False,
        )
        self._thread.start()

    @property
    def run_id(self) -> str:
        return self._writer.run_id

    @property
    def root(self) -> Path:
        return self._writer.root

    @property
    def manifest(self) -> dict[str, Any]:
        return self._writer.manifest

    def _raise_worker_error(self) -> None:
        if self._error is not None:
            raise RuntimeError("async telemetry worker failed") from self._error

    def append(
        self,
        record: Any,
        *,
        rich_state: Mapping[str, Any],
        full_snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("async telemetry writer is closed")
        self._raise_worker_error()
        self._queue.put((record, rich_state, full_snapshot))
        self._submitted += 1
        self._raise_worker_error()

    def _run(self) -> None:
        try:
            while True:
                item = self._queue.get()
                try:
                    if item is self._STOP:
                        return
                    if self._error is not None:
                        continue
                    record, rich_state, full_snapshot = cast(
                        tuple[Any, Mapping[str, Any], Mapping[str, Any] | None], item
                    )
                    self._writer.append(
                        record,
                        rich_state=rich_state,
                        full_snapshot=full_snapshot,
                    )
                except BaseException as exc:
                    self._error = exc
                finally:
                    self._queue.task_done()
        finally:
            try:
                self._writer.close()
            except BaseException as exc:
                if self._error is None:
                    self._error = exc

    def flush(self) -> None:
        if self._closed:
            self._raise_worker_error()
            return
        self._queue.join()
        self._raise_worker_error()

    def close(self) -> None:
        if self._closed:
            self._raise_worker_error()
            return
        self._closed = True
        self._queue.put(self._STOP)
        self._queue.join()
        self._thread.join()
        self._raise_worker_error()
