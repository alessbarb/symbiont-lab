"""Passive adapter from Physics3D viewer frames to observer telemetry."""
from __future__ import annotations

import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Protocol

from .contracts import ObservedFrame
from .projection import mind_snapshot_from_rich_state, runtime_tick_events



def _body_descriptor_for_state(physical_state: Mapping[str, object]):
    from symbiont_lab.physics3d.bodies import DEFAULT_BODY_REGISTRY

    body_kind = str(physical_state.get("body_kind") or "anthropomorphic-v6")
    try:
        return DEFAULT_BODY_REGISTRY.get(body_kind)
    except ValueError:
        return DEFAULT_BODY_REGISTRY.get("anthropomorphic-v6")


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

    def publish_pose_frame(
        self,
        *,
        physical_state: Mapping[str, object],
        tick: int,
        substep_index: int,
        physics_step: int,
        simulation_time_s: float,
        tick_simulation_span_s: float,
    ) -> None:
        """Publish one lightweight observer-only physical pose frame."""
        if self._stop.is_set():
            return

        descriptor = _body_descriptor_for_state(physical_state)
        joint_specs = descriptor.observer_joint_specs
        joints: list[dict[str, object]] = []

        raw_joints = physical_state.get("joints", ())
        if isinstance(raw_joints, (list, tuple)):
            for item in raw_joints:
                if not isinstance(item, Mapping):
                    continue
                try:
                    index = int(item.get("joint_index", -1))
                except (TypeError, ValueError):
                    continue
                name = (
                    joint_specs[index].name
                    if 0 <= index < len(joint_specs)
                    else f"joint_{index}"
                )
                try:
                    position = float(item["position"])
                except (KeyError, TypeError, ValueError):
                    continue
                joints.append({"name": name, "position": position})

        links: list[dict[str, object]] = []
        raw_links = physical_state.get("links", ())
        if isinstance(raw_links, (list, tuple)):
            for item in raw_links:
                if not isinstance(item, Mapping):
                    continue
                position = item.get("position")
                orientation = item.get("orientation")
                if (
                    item.get("link_name") is None
                    or not isinstance(position, (list, tuple))
                    or len(position) != 3
                    or not isinstance(orientation, (list, tuple))
                    or len(orientation) != 4
                ):
                    continue
                try:
                    links.append(
                        {
                            "name": str(item["link_name"]),
                            "position": [float(value) for value in position],
                            "orientation": [float(value) for value in orientation],
                        }
                    )
                except (TypeError, ValueError):
                    continue

        event: dict[str, Any] = {
            "type": "body_pose",
            "source": "physics3d",
            "body_kind": descriptor.body_kind,
            "tick": int(tick),
            "substep_index": int(substep_index),
            "physics_step": int(physics_step),
            "simulation_time_s": float(simulation_time_s),
            "tick_simulation_span_s": float(tick_simulation_span_s),
            "joints": joints,
            "links": links,
            "provenance": {
                "owner": "observer",
                "feeds_back": False,
                "sampling_hz": 60,
            },
        }
        base_position = physical_state.get("base_position")
        if isinstance(base_position, (list, tuple)) and len(base_position) == 3:
            event["base_position"] = [float(value) for value in base_position]
        base_orientation = physical_state.get("base_orientation")
        if isinstance(base_orientation, (list, tuple)) and len(base_orientation) == 4:
            event["base_orientation"] = [float(value) for value in base_orientation]

        center_of_mass = physical_state.get("center_of_mass")
        if isinstance(center_of_mass, (list, tuple)) and len(center_of_mass) == 3:
            try:
                event["center_of_mass"] = [float(value) for value in center_of_mass]
            except (TypeError, ValueError):
                pass

        raw_contacts = physical_state.get("contacts", ())
        contacts: list[dict[str, object]] = []
        if isinstance(raw_contacts, (list, tuple)):
            for item in raw_contacts:
                if not isinstance(item, Mapping):
                    continue
                position = item.get("position")
                normal = item.get("normal")
                if (
                    not isinstance(position, (list, tuple))
                    or len(position) != 3
                    or not isinstance(normal, (list, tuple))
                    or len(normal) != 3
                ):
                    continue
                try:
                    contacts.append(
                        {
                            "link_name": str(item.get("link_name", "")),
                            "position": [float(value) for value in position],
                            "normal": [float(value) for value in normal],
                            "normal_force": max(0.0, float(item.get("normal_force", 0.0))),
                        }
                    )
                except (TypeError, ValueError):
                    continue
        if contacts:
            event["contacts"] = contacts
        self._sink.push(event)

    def publish(self, snapshot: Any, *, physical_state: dict[str, object]) -> None:
        if self._stop.is_set():
            return

        if is_dataclass(snapshot):
            record = asdict(snapshot)
        elif isinstance(snapshot, Mapping):
            record = dict(snapshot)
        else:
            raise TypeError("Physics3D snapshot must be a dataclass or mapping")

        descriptor = _body_descriptor_for_state(physical_state)
        joint_specs = descriptor.observer_joint_specs
        joints: list[dict[str, object]] = []

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
                if 0 <= index < len(joint_specs):
                    joint["name"] = joint_specs[index].name
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
            "body_kind": descriptor.body_kind,
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
