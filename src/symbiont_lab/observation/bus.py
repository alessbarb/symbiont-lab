"""Thread-safe fan-out bus for passive organism observation events."""

from __future__ import annotations

import json
import queue
import threading
from collections import deque
from copy import deepcopy
from typing import Any

from .delta import ObservationDeltaEncoder
from .world_scene import apply_world_event

_DEFAULT_QUEUE_SIZE = 2048
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
        anchor_interval: int = 32,
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
        self._world_scene: dict | None = None
        self._delta = ObservationDeltaEncoder(anchor_interval=anchor_interval)

    def push(self, event: dict[str, Any]) -> int:
        with self._lock:
            if event.get("type") == "world_scene":
                self._world_scene = apply_world_event(self._world_scene, event)

            encoded = self._delta.encode(event)
            self._sequence += 1
            stream_id = self._sequence
            projected = dict(encoded)
            projected["_stream_id"] = stream_id
            data = json.dumps(projected, separators=(",", ":"), ensure_ascii=False)

            event_type = str(event.get("type") or "")
            if event_type:
                if event_type == "world_scene":
                    self._last_by_type[event_type] = json.dumps(
                        {**self._world_scene, "_stream_id": stream_id},
                        separators=(",", ":"),
                    )
                elif projected.get("type") == "observation_delta":
                    anchor = self._delta.anchor(event_type)
                    if anchor is not None:
                        self._last_by_type[event_type] = json.dumps(
                            {**anchor, "_stream_id": stream_id},
                            separators=(",", ":"),
                            ensure_ascii=False,
                        )
                else:
                    self._last_by_type[event_type] = data

            self._history.append((stream_id, data))
            overflow_data = (
                self._last_by_type.get(event_type, data)
                if projected.get("type") == "observation_delta"
                else data
            )
            for consumer in self._queues:
                selected = data
                if consumer.full():
                    try:
                        consumer.get_nowait()
                    except queue.Empty:
                        pass
                    # A dropped delta invalidates the consumer's channel base.
                    # Replace the current message with a materialized anchor so
                    # the next message is immediately self-healing.
                    selected = overflow_data
                try:
                    consumer.put_nowait(selected)
                except queue.Full:
                    pass
            return stream_id

    def subscribe(self, after_sequence: int | None = None) -> queue.Queue[str]:
        consumer: queue.Queue[str] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            replay: list[str]
            history = list(self._history)
            history_floor = history[0][0] if history else self._sequence + 1
            if after_sequence is None:
                replay = list(self._last_by_type.values())
            elif int(after_sequence) < history_floor - 1:
                # The requested resume point fell out of retained history.
                # Replay materialized anchors/current states rather than a delta
                # chain with an unknowable missing base revision.
                replay = list(self._last_by_type.values())
            else:
                replay = [
                    data for stream_id, data in history if stream_id > int(after_sequence)
                ]
            for data in replay[-self._queue_size :]:
                if consumer.full():
                    consumer.get_nowait()
                consumer.put_nowait(data)
            self._queues.append(consumer)
        return consumer

    def world_scene(self) -> dict | None:
        """Atomic materialized scene for initial loads and dropped-delta recovery."""
        with self._lock:
            return deepcopy(self._world_scene)

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
