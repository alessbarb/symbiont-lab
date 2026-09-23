"""Thread-safe fan-out bus for passive organism observation events."""
from __future__ import annotations

import json
import queue
import threading
from typing import Any

_DEFAULT_QUEUE_SIZE = 64


class ObservationBus:
    """Pub-sub hub: one or more producers -> bounded consumer queues."""

    def __init__(self, *, queue_size: int = _DEFAULT_QUEUE_SIZE) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._queue_size = int(queue_size)
        self._lock = threading.Lock()
        self._queues: list[queue.Queue[str]] = []
        self._last_by_type: dict[str, str] = {}

    def push(self, event: dict[str, Any]) -> None:
        """Push an event, dropping stale queued telemetry for slow consumers."""
        data = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            event_type = str(event.get("type") or "")
            if event_type:
                self._last_by_type[event_type] = data
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

    def subscribe(self) -> queue.Queue[str]:
        """Register a consumer and replay the latest state of each event type."""
        consumer: queue.Queue[str] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            for data in self._last_by_type.values():
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
