"""Thread-safe fan-out bus for passive organism observation events."""

from __future__ import annotations

import json
import queue
import threading
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .delta import COMPRESSIBLE_TYPES, ObservationDeltaEncoder
from .world_scene import apply_world_event

_DEFAULT_QUEUE_SIZE = 2048
_DEFAULT_HISTORY_SIZE = 512
_DEPENDENT_TYPES = COMPRESSIBLE_TYPES | {"world_scene"}


@dataclass(frozen=True, slots=True)
class ObservationMessage:
    """Serialized observer payload paired with its transport identity."""

    stream_id: int
    data: bytes


class ObservationBus:
    """Pub-sub hub with bounded consumers and reconnect replay.

    Events are presentation projections, not organism state. A monotonically
    increasing transport stream id is paired with serialized payload bytes at
    this boundary so SSE can resume without mutating observer JSON contracts.
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
        # Channels with a base either delivered or queued in FIFO order. Only
        # dependency-bearing channels are tracked, so this is bounded per client.
        self._queues: dict[queue.Queue[ObservationMessage], set[str]] = {}
        self._last_by_type: dict[str, ObservationMessage] = {}
        self._last_sequence_by_type: dict[str, int] = {}
        self._history: deque[ObservationMessage] = deque(maxlen=int(history_size))
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
            data = json.dumps(
                projected,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")

            event_type = str(event.get("type") or "")
            if event_type:
                if event_type == "world_scene":
                    self._last_by_type[event_type] = ObservationMessage(
                        stream_id=stream_id,
                        data=json.dumps(
                            self._world_scene,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode("utf-8"),
                    )
                elif projected.get("type") == "observation_delta":
                    anchor = self._delta.anchor(event_type)
                    if anchor is not None:
                        self._last_by_type[event_type] = ObservationMessage(
                            stream_id=stream_id,
                            data=json.dumps(
                                anchor,
                                separators=(",", ":"),
                                ensure_ascii=False,
                            ).encode("utf-8"),
                        )
                else:
                    self._last_by_type[event_type] = ObservationMessage(
                        stream_id=stream_id,
                        data=data,
                    )
                self._last_sequence_by_type[event_type] = stream_id

            message = ObservationMessage(stream_id=stream_id, data=data)
            # Reconnect cursors identify transport messages, not the client's
            # per-channel bases (which an earlier overflow may have dropped).
            # Keep bounded materialized history so replay is self-contained.
            self._history.append(
                self._last_by_type[event_type] if event_type in _DEPENDENT_TYPES else message
            )
            for consumer, based_channels in self._queues.items():
                if consumer.full():
                    # Any retained delta may depend on a dropped message, even
                    # when it belongs to a different channel from this event.
                    # Drop the pending presentation backlog and lazily rebase
                    # each channel; never block the subject on a slow observer.
                    while True:
                        try:
                            consumer.get_nowait()
                        except queue.Empty:
                            break
                    based_channels.clear()
                selected = message
                if event_type in _DEPENDENT_TYPES:
                    if event_type not in based_channels:
                        selected = self._last_by_type[event_type]
                    based_channels.add(event_type)
                consumer.put_nowait(selected)
            return stream_id

    def subscribe(
        self,
        after_sequence: int | None = None,
    ) -> queue.Queue[ObservationMessage]:
        consumer: queue.Queue[ObservationMessage] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            replay: list[ObservationMessage]
            history = list(self._history)
            history_floor = history[0].stream_id if history else self._sequence + 1
            current = [
                self._last_by_type[event_type]
                for event_type in sorted(
                    self._last_by_type,
                    key=lambda item: self._last_sequence_by_type.get(item, 0),
                )
            ]
            based_channels: set[str] = set()
            if after_sequence is None or int(after_sequence) < history_floor - 1:
                replay = current
            else:
                replay = [message for message in history if message.stream_id > int(after_sequence)]
                if len(replay) > self._queue_size:
                    # Slicing a delta chain would discard required revisions.
                    replay = current
            for message in replay[-self._queue_size :]:
                consumer.put_nowait(message)
                payload = json.loads(message.data)
                channel = str(payload.get("channel") or payload.get("type") or "")
                if channel in _DEPENDENT_TYPES:
                    based_channels.add(channel)
            self._queues[consumer] = based_channels
        return consumer

    def recent_materialized(
        self,
        event_type: str,
        *,
        limit: int = 128,
    ) -> list[dict[str, Any]]:
        """Return bounded materialized observer events without exposing delta state."""
        wanted = str(event_type)
        bounded_limit = max(1, min(int(limit), self._history.maxlen or int(limit)))
        with self._lock:
            messages = list(self._history)

        result: list[dict[str, Any]] = []
        for message in messages:
            try:
                payload = json.loads(message.data)
            except (TypeError, ValueError):
                continue
            state: Any = payload
            if (
                isinstance(payload, dict)
                and payload.get("type") == "observation_delta"
                and payload.get("kind") == "anchor"
            ):
                state = payload.get("state")
            if not isinstance(state, dict) or state.get("type") != wanted:
                continue
            result.append(deepcopy(state))
        return result[-bounded_limit:]

    def world_scene(self) -> dict | None:
        """Atomic materialized scene for initial loads and dropped-delta recovery."""
        with self._lock:
            return deepcopy(self._world_scene)

    def unsubscribe(self, consumer: queue.Queue[ObservationMessage]) -> None:
        with self._lock:
            self._queues.pop(consumer, None)

    @property
    def has_data(self) -> bool:
        with self._lock:
            return bool(self._last_by_type)

    @property
    def latest_sequence(self) -> int:
        with self._lock:
            return self._sequence
