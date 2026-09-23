"""Passive adapter from Physics3D viewer frames to observer telemetry."""
from __future__ import annotations

import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Protocol

from .contracts import ObservedFrame
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
        self._pending_frames: dict[int, dict[str, Any]] = {}

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

        links: list[dict[str, object]] = []
        raw_links = physical_state.get("links", ())
        if isinstance(raw_links, (list, tuple)):
            for item in raw_links:
                if not isinstance(item, Mapping):
                    continue
                raw_position = item.get("position")
                raw_orientation = item.get("orientation")
                if (
                    item.get("link_name") is None
                    or not isinstance(raw_position, (list, tuple))
                    or len(raw_position) != 3
                    or not isinstance(raw_orientation, (list, tuple))
                    or len(raw_orientation) != 4
                ):
                    continue
                try:
                    links.append(
                        {
                            "name": str(item["link_name"]),
                            "position": [float(value) for value in raw_position],
                            "orientation": [float(value) for value in raw_orientation],
                        }
                    )
                except (TypeError, ValueError):
                    continue

        projected = {
            **record,
            "source": "physics3d",
            "joints": joints,
            "links": links,
        }
        if physical_state.get("base_position") is not None:
            projected["base_position"] = physical_state["base_position"]
        elif record.get("base_position") is not None:
            projected["base_position"] = record["base_position"]
        if physical_state.get("base_orientation") is not None:
            projected["base_orientation"] = physical_state["base_orientation"]
        elif record.get("base_orientation") is not None:
            projected["base_orientation"] = record["base_orientation"]

        raw_resource = physical_state.get("locomotion_resource")
        if isinstance(raw_resource, Mapping):
            position = raw_resource.get("position")
            if isinstance(position, (list, tuple)) and len(position) == 3:
                try:
                    projected["resource_position"] = [float(value) for value in position]
                except (TypeError, ValueError):
                    pass

        frame_tick = None
        try:
            frame_tick = int(projected.get("tick"))
        except (TypeError, ValueError):
            pass

        components: dict[str, Any] = {}
        for event in runtime_tick_events(projected):
            self._sink.push(event)
            event_type = str(event.get("type") or "")
            if event_type:
                components[event_type] = dict(event)
        if frame_tick is not None:
            self._pending_frames[frame_tick] = components
            # Rendering is deliberately sparse, so only a tiny number of
            # not-yet-paired frames should ever exist.
            for stale_tick in sorted(self._pending_frames)[:-4]:
                self._pending_frames.pop(stale_tick, None)

    def publish_rich_state(self, rich_state: Mapping[str, Any]) -> None:
        if self._stop.is_set():
            return
        snapshot = mind_snapshot_from_rich_state(rich_state)
        tick = snapshot.get("tick")
        try:
            frame_tick = int(tick)
        except (TypeError, ValueError):
            frame_tick = None

        mind_event = {
            "type": "mind_snapshot",
            "source": "physics3d",
            "tick": tick,
            "organism_id": rich_state.get("organism_id"),
            "snapshot": snapshot,
            "coherent_frame_follows": frame_tick is not None,
        }
        self._sink.push(mind_event)

        if frame_tick is None:
            return
        components = self._pending_frames.pop(frame_tick, {})
        frame = ObservedFrame(
            tick=frame_tick,
            source="physics3d",
            organism_id=(
                str(rich_state["organism_id"])
                if rich_state.get("organism_id") is not None
                else None
            ),
            body=components.get("body"),
            cognition=components.get("cognition"),
            vitals=components.get("vitals"),
            mind=snapshot,
        )
        self._sink.push(frame.as_event())

    def close(self) -> None:
        self.request_stop()
