"""Thread-safe fan-out bus for passive organism observation events."""

from __future__ import annotations

import json
import queue
import threading
from collections import deque
from typing import Any

_DEFAULT_QUEUE_SIZE = 64
_DEFAULT_HISTORY_SIZE = 512


class ObservationBus:
    """Pub-sub hub with bounded consumers and reconnect replay.

    Events are presentation projections, not organism state. A monotonically
    increasing transport stream id is added at this boundary so SSE can resume
    without altering scientific telemetry contracts.
    """

    def __init__(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
        history_size: int = _DEFAULT_HISTORY_SIZE,
    ) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        if history_size < 1:
            raise ValueError("history_size must be >= 1")
        self._queue_size = int(queue_size)
        self._lock = threading.Lock()
        self._queues: list[queue.Queue[str]] = []
        self._last_by_type: dict[str, str] = {}
        self._history: deque[tuple[int, str]] = deque(maxlen=int(history_size))
        self._sequence = 0

    def push(self, event: dict[str, Any]) -> int:
        with self._lock:
            self._sequence += 1
            stream_id = self._sequence
            projected = dict(event)
            projected["_stream_id"] = stream_id
            data = json.dumps(projected, separators=(",", ":"), ensure_ascii=False)
            event_type = str(projected.get("type") or "")
            if event_type:
                self._last_by_type[event_type] = data
            self._history.append((stream_id, data))
            for consumer in self._queues:
                if consumer.full():
                    try:
                        consumer.get_nowait()
                    except queue.Empty:
                        pass
                try:
                    consumer.put_nowait(data)
                except queue.Full:
                    pass
            return stream_id

    def subscribe(self, after_sequence: int | None = None) -> queue.Queue[str]:
        consumer: queue.Queue[str] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            if after_sequence is None:
                replay = list(self._last_by_type.values())
            else:
                replay = [
                    data for stream_id, data in self._history if stream_id > int(after_sequence)
                ]
            for data in replay[-self._queue_size :]:
                if consumer.full():
                    consumer.get_nowait()
                consumer.put_nowait(data)
            self._queues.append(consumer)
        return consumer

    def unsubscribe(self, consumer: queue.Queue[str]) -> None:
        with self._lock:
            try:
                self._queues.remove(consumer)
            except ValueError:
                pass

    @property
    def has_data(self) -> bool:
        with self._lock:
            return bool(self._last_by_type)

    @property
    def latest_sequence(self) -> int:
        with self._lock:
            return self._sequence
