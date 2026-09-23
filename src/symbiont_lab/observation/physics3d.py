"""Passive adapter from Physics3D viewer frames to observer telemetry."""
from __future__ import annotations

import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Protocol

from .projection import mind_snapshot_from_rich_state, runtime_tick_events


class EventSink(Protocol):
    def push(self, event: dict[str, Any]) -> None: ...


class Physics3DObservationBridge:
    """Viewer-compatible passive bridge.

    The only reverse path is lifecycle stop; it cannot provide motor, learning,
    reward, environment, or cognitive commands.
    """

    def __init__(self, sink: EventSink) -> None:
        self._sink = sink
        self._stop = threading.Event()

    def start(self) -> None:
        return None

    @property
    def is_alive(self) -> bool:
        return not self._stop.is_set()

    def poll_commands(self) -> list[dict[str, Any]]:
        return [{"type": "stop"}] if self._stop.is_set() else []

    def poll_stop(self) -> bool:
        return self._stop.is_set()

    def request_stop(self) -> None:
        self._stop.set()

    def publish(self, snapshot: Any, *, physical_state: dict[str, object]) -> None:
        if self._stop.is_set():
            return

        if is_dataclass(snapshot):
            record = asdict(snapshot)
        elif isinstance(snapshot, Mapping):
            record = dict(snapshot)
        else:
            raise TypeError("Physics3D snapshot must be a dataclass or mapping")

        joints: list[dict[str, object]] = []
        try:
            from symbiont_lab.physics3d.humanoid import JOINT_SPECS
        except ImportError:
            JOINT_SPECS = ()

        raw_joints = physical_state.get("joints", ())
        if isinstance(raw_joints, (list, tuple)):
            for item in raw_joints:
                if not isinstance(item, Mapping):
                    continue
                try:
                    index = int(item.get("joint_index", -1))
                except (TypeError, ValueError):
                    continue
                joint: dict[str, object] = {}
                if 0 <= index < len(JOINT_SPECS):
                    joint["name"] = JOINT_SPECS[index].name
                else:
                    joint["name"] = f"joint_{index}"
                if item.get("position") is not None:
                    try:
                        joint["position"] = float(item["position"])
                    except (TypeError, ValueError):
                        pass
                joints.append(joint)

        projected = {**record, "source": "physics3d", "joints": joints}
        if physical_state.get("base_position") is not None:
            projected["base_position"] = physical_state["base_position"]
        elif record.get("base_position") is not None:
            projected["base_position"] = record["base_position"]
        if physical_state.get("base_orientation") is not None:
            projected["base_orientation"] = physical_state["base_orientation"]
        elif record.get("base_orientation") is not None:
            projected["base_orientation"] = record["base_orientation"]

        for event in runtime_tick_events(projected):
            self._sink.push(event)

    def publish_rich_state(self, rich_state: Mapping[str, Any]) -> None:
        if self._stop.is_set():
            return
        snapshot = mind_snapshot_from_rich_state(rich_state)
        self._sink.push({
            "type": "mind_snapshot",
            "source": "physics3d",
            "tick": snapshot.get("tick"),
            "organism_id": rich_state.get("organism_id"),
            "snapshot": snapshot,
        })

    def close(self) -> None:
        self.request_stop()
