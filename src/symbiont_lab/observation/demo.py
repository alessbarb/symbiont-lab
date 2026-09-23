"""Explicit synthetic telemetry producer for UI development only."""
from __future__ import annotations

import math
import threading
from typing import Any, Protocol


class EventSink(Protocol):
    def push(self, event: dict[str, Any]) -> None: ...


class DemoOrganismTelemetry:
    """Synthetic telemetry for explicit UI-development mode only."""

    def __init__(self, sink: EventSink, *, interval: float = 0.75) -> None:
        self._sink = sink
        self._interval = float(interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
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
            common = {"source": "demo", "run_id": "demo", "instance_id": "demo", "tick": self._tick}
            self._sink.push({
                **common,
                "type": "body",
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
            })
            self._sink.push({
                **common,
                "type": "cognition",
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
            })
            self._sink.push({
                **common,
                "type": "vitals",
                "alive": True,
                "joint_motion": 0.22 + 0.1 * math.sin(phase / 13),
                "resource_progress": 0.48 + 0.12 * math.sin(phase / 12),
                "displacement_from_origin": 0.12 * phase,
                "mechanical_work_joules": 0.9 + 0.2 * math.sin(phase / 10),
                "metabolic_work_cost": 0.15 + 0.05 * math.sin(phase / 9),
            })
