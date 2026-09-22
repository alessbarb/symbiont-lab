"""Thread-safe fan-out of live organism telemetry to SSE subscribers.

This module is purely transport — it never imports cognition internals.
Physics3D / organism runtime push structured events here; SSE handler
threads pull them out and send them to connected browsers.
"""
from __future__ import annotations

import json
import math
import queue
import threading
import time
from typing import Any, Mapping


class OrganismStream:
    """Pub-sub hub: one producer (Physics3D bridge) → N SSE consumers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: list[queue.SimpleQueue] = []
        # Cache the last event of each type so new subscribers get state fast.
        self._last_by_type: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Producer side
    # ------------------------------------------------------------------

    def push(self, event: dict[str, Any]) -> None:
        """Push a structured event dict to all current subscribers."""
        data = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            event_type = event.get("type", "")
            if event_type:
                self._last_by_type[event_type] = data
            dead: list[queue.SimpleQueue] = []
            for q in self._queues:
                try:
                    q.put_nowait(data)
                except Exception:
                    dead.append(q)
            for q in dead:
                self._queues.remove(q)

    # ------------------------------------------------------------------
    # Consumer side
    # ------------------------------------------------------------------

    def subscribe(self) -> queue.SimpleQueue:
        """Register a new SSE client. Returns a queue of serialized events."""
        q: queue.SimpleQueue = queue.SimpleQueue()
        with self._lock:
            # Replay latest snapshot of each type so the UI isn't blank.
            for data in self._last_by_type.values():
                q.put(data)
            self._queues.append(q)
        return q

    def unsubscribe(self, q: queue.SimpleQueue) -> None:
        with self._lock:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    @property
    def has_data(self) -> bool:
        return bool(self._last_by_type)


def stream_runtime_tick(stream: OrganismStream, tick: Mapping[str, Any]) -> None:
    """Translate a canonical runtime tick into the browser-friendly body/cognition/vitals stream."""
    if not isinstance(tick, Mapping):
        raise TypeError("tick must be a mapping")

    body = {
        "type": "body",
        "tick": int(tick.get("tick", 0) or 0),
        "base_position": [float(v) for v in (tick.get("base_position") or [0.0, 1.0, 0.0])],
        "base_orientation": [float(v) for v in (tick.get("base_orientation") or [0.0, 0.0, 0.0, 1.0])],
        "joints": [
            {
                "name": str(item.get("name", "joint")),
                "position": float(item.get("position", 0.0)),
            }
            for item in tick.get("joints", [])
            if isinstance(item, Mapping)
        ],
        "contact_count": int(tick.get("contact_count", 0) or 0),
        "metabolic_reserve": float(tick.get("metabolic_reserve_ratio", tick.get("metabolic_reserve", 0.6))),
    }

    cognition = {
        "type": "cognition",
        "tick": int(tick.get("tick", 0) or 0),
        "schema_confidence": float(tick.get("schema_confidence", 0.0) or 0.0),
        "schema_parts": int(tick.get("schema_parts", 0) or 0),
        "schema_sensory_parts": int(tick.get("schema_sensory_parts", 0) or 0),
        "schema_cognitive_regions": int(tick.get("schema_cognitive_regions", 0) or 0),
        "motor_origin": str(tick.get("motor_origin", "none") or "none"),
        "predictor_count": int(tick.get("predictor_count", 0) or 0),
        "prediction_error": tick.get("prediction_error"),
        "slm_active": bool(tick.get("slm_active", False)),
        "prospective_selected": bool(tick.get("prospective_selected", False)),
        "prospective_expected_value": tick.get("prospective_expected_value"),
    }

    vitals = {
        "type": "vitals",
        "tick": int(tick.get("tick", 0) or 0),
        "alive": bool(tick.get("alive", True)),
        "joint_motion": float(tick.get("joint_motion", 0.0) or 0.0),
        "resource_progress": float(tick.get("resource_progress", 0.0) or 0.0),
        "displacement_from_origin": float(tick.get("displacement_from_origin", 0.0) or 0.0),
        "mechanical_work_joules": float(tick.get("mechanical_work_joules", 0.0) or 0.0),
        "metabolic_work_cost": float(tick.get("metabolic_work_cost", 0.0) or 0.0),
    }

    stream.push(body)
    stream.push(cognition)
    stream.push(vitals)


class DemoOrganismTelemetry:
    """Synthetic live stream used when no real organism runtime is attached."""

    def __init__(self, stream: OrganismStream, *, interval: float = 0.75) -> None:
        self._stream = stream
        self._interval = float(interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            self._tick += 1
            phase = self._tick % 40
            body = {
                "type": "body",
                "tick": self._tick,
                "base_position": [0.1 * math.sin(phase / 7), 1.05, 0.1 * math.cos(phase / 9)],
                "base_orientation": [0.0, 0.0, math.sin(phase / 10), math.cos(phase / 10)],
                "joints": [
                    {"name": "trunk_yaw", "position": 0.12 * math.sin(phase / 8)},
                    {"name": "left_shoulder_pitch", "position": 0.35 * math.sin(phase / 5)},
                    {"name": "right_shoulder_pitch", "position": -0.35 * math.sin(phase / 5)},
                    {"name": "left_hip_pitch", "position": 0.18 * math.sin(phase / 6)},
                    {"name": "right_hip_pitch", "position": -0.18 * math.sin(phase / 6)},
                ],
                "contact_count": 2 if phase % 9 else 1,
                "metabolic_reserve": min(1.0, 0.6 + 0.25 * math.sin(phase / 10)),
            }
            cognition = {
                "type": "cognition",
                "tick": self._tick,
                "schema_confidence": 0.82 + 0.1 * math.sin(phase / 11),
                "schema_parts": 27,
                "schema_sensory_parts": 11,
                "schema_cognitive_regions": 9,
                "motor_origin": "cognition" if phase % 13 else "babbling",
                "predictor_count": 18 + (phase % 7),
                "prediction_error": 0.12 + 0.04 * math.sin(phase / 8),
                "slm_active": phase % 14 < 8,
                "prospective_selected": phase % 11 == 0,
                "prospective_expected_value": 0.62 + 0.08 * math.sin(phase / 7),
            }
            vitals = {
                "type": "vitals",
                "tick": self._tick,
                "alive": True,
                "joint_motion": 0.22 + 0.1 * math.sin(phase / 13),
                "resource_progress": 0.48 + 0.12 * math.sin(phase / 12),
                "displacement_from_origin": 0.12 * phase,
                "mechanical_work_joules": 0.9 + 0.2 * math.sin(phase / 10),
                "metabolic_work_cost": 0.15 + 0.05 * math.sin(phase / 9),
            }
            self._stream.push(body)
            self._stream.push(cognition)
            self._stream.push(vitals)
