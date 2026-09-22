"""Thread-safe fan-out of live organism telemetry to SSE subscribers.

This module is transport/projection only. It does not import cognition internals.
"""
from __future__ import annotations

import json
import math
import queue
import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

_DEFAULT_QUEUE_SIZE = 64


class OrganismStream:
    """Pub-sub hub: one or more producers -> bounded SSE consumer queues."""

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
                    # Another producer may have raced us. Latest-state telemetry
                    # is preferable to unbounded backlog.
                    pass

    def subscribe(self) -> queue.Queue[str]:
        """Register a client and replay the latest state of each event type."""
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


def _identity(tick: Mapping[str, Any]) -> dict[str, Any]:
    """Copy optional canonical identity fields without inventing them."""
    result: dict[str, Any] = {"source": str(tick.get("source") or "runtime")}
    if tick.get("instance_id") is not None:
        result["instance_id"] = str(tick["instance_id"])
    if tick.get("run_id") is not None:
        result["run_id"] = str(tick["run_id"])
    if tick.get("sequence") is not None:
        try:
            result["sequence"] = int(tick["sequence"])
        except (TypeError, ValueError):
            pass
    return result


def stream_runtime_tick(stream: OrganismStream, tick: Mapping[str, Any]) -> None:
    """Project one canonical runtime tick into body/cognition/vitals telemetry."""
    if not isinstance(tick, Mapping):
        raise TypeError("tick must be a mapping")

    identity = _identity(tick)
    tick_number = int(tick.get("tick", 0) or 0)

    body = {
        **identity,
        "type": "body",
        "tick": tick_number,
        "base_position": [float(v) for v in (tick.get("base_position") or [0.0, 1.0, 0.0])],
        "base_orientation": [float(v) for v in (tick.get("base_orientation") or [0.0, 0.0, 0.0, 1.0])],
        "joints": [
            {"name": str(item.get("name", "joint")), "position": float(item.get("position", 0.0))}
            for item in tick.get("joints", [])
            if isinstance(item, Mapping)
        ],
        "contact_count": int(tick.get("contact_count", 0) or 0),
        "metabolic_reserve": float(
            tick.get("metabolic_reserve_ratio", tick.get("metabolic_reserve", 0.6))
        ),
    }

    cognition = {
        **identity,
        "type": "cognition",
        "tick": tick_number,
        "schema_confidence": float(tick.get("schema_confidence", 0.0) or 0.0),
        "schema_parts": int(tick.get("schema_parts", 0) or 0),
        "schema_sensory_parts": int(tick.get("schema_sensory_parts", 0) or 0),
        "schema_cognitive_regions": int(tick.get("schema_cognitive_regions", 0) or 0),
        "motor_origin": str(tick.get("motor_origin", "none") or "none"),
        "motor_origin_detail": str(tick.get("motor_origin_detail", "") or ""),
        "predictor_count": int(tick.get("predictor_count", 0) or 0),
        "sensorimotor_patterns": int(tick.get("sensorimotor_patterns", 0) or 0),
        "motor_primitives": int(tick.get("motor_primitives", 0) or 0),
        "cognitive_motor_primitives": int(tick.get("cognitive_motor_primitives", 0) or 0),
        "prediction_error": tick.get("prediction_error"),
        "slm_active": bool(tick.get("slm_active", False)),
        "slm_models": tick.get("slm_models"),
        "prospective_selected": bool(tick.get("prospective_selected", False)),
        "prospective_expected_value": tick.get("prospective_expected_value"),
    }

    vitals = {
        **identity,
        "type": "vitals",
        "tick": tick_number,
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
    """Synthetic telemetry for explicit UI-development mode only."""

    def __init__(self, stream: OrganismStream, *, interval: float = 0.75) -> None:
        self._stream = stream
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
            self._stream.push({
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
            self._stream.push({
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
            self._stream.push({
                **common,
                "type": "vitals",
                "alive": True,
                "joint_motion": 0.22 + 0.1 * math.sin(phase / 13),
                "resource_progress": 0.48 + 0.12 * math.sin(phase / 12),
                "displacement_from_origin": 0.12 * phase,
                "mechanical_work_joules": 0.9 + 0.2 * math.sin(phase / 10),
                "metabolic_work_cost": 0.15 + 0.05 * math.sin(phase / 9),
            })


class Physics3DStreamBridge:
    """Passive Physics3D viewer bridge that projects evaluator frames to SSE.

    Implements the same viewer contract used by Physics3D CLI without creating
    a desktop window or introducing any control path into cognition.
    """

    def __init__(self, stream: OrganismStream) -> None:
        self._stream = stream
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
                name = (
                    JOINT_SPECS[index].name
                    if 0 <= index < len(JOINT_SPECS)
                    else f"joint_{index}"
                )
                joints.append({
                    "name": name,
                    "position": float(item.get("position", 0.0) or 0.0),
                })

        projected = {
            **record,
            "source": "physics3d",
            "base_position": physical_state.get(
                "base_position",
                record.get("base_position", [0.0, 0.0, 1.0]),
            ),
            "base_orientation": physical_state.get(
                "base_orientation",
                record.get("base_orientation", [0.0, 0.0, 0.0, 1.0]),
            ),
            "joints": joints,
            "alive": bool(record.get("alive", True)),
        }
        stream_runtime_tick(self._stream, projected)

    def publish_rich_state(self, rich_state: Mapping[str, Any]) -> None:
        if self._stop.is_set():
            return
        stream_runtime_mind_snapshot(self._stream, rich_state)

    def close(self) -> None:
        self.request_stop()


def _prediction_class(value: object) -> str:
    try:
        error = abs(float(value))
    except (TypeError, ValueError):
        return "trace"
    if error <= 1e-12:
        return "zero"
    if error < 0.01:
        return "trace"
    if error < 0.05:
        return "low"
    if error < 0.15:
        return "medium"
    if error < 0.4:
        return "high"
    return "extreme"


def _mind_snapshot_from_rich_state(rich_state: Mapping[str, Any]) -> dict[str, Any]:
    """Translate Physics3D passive telemetry into the Mind view contract."""
    runtime = rich_state.get("runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    cognition = rich_state.get("cognition")
    cognition = cognition if isinstance(cognition, Mapping) else {}
    topology = rich_state.get("cognitive_topology")
    topology = topology if isinstance(topology, Mapping) else None
    post = rich_state.get("post")
    post = post if isinstance(post, Mapping) else {}

    senses: list[dict[str, Any]] = []
    raw_percepts = runtime.get("percepts", ())
    if isinstance(raw_percepts, (list, tuple)):
        for index, item in enumerate(raw_percepts[:64]):
            if not isinstance(item, Mapping):
                continue
            sense_id = str(
                item.get("name")
                or item.get("capability_id")
                or item.get("id")
                or f"sense.{index}"
            )
            quality = item.get("quality")
            available = item.get("available")
            active = bool(available) if available is not None else str(quality).lower() not in {
                "unavailable", "none", "missing",
            }
            senses.append({
                "id": sense_id,
                "name": sense_id,
                "active": active,
                "quality": quality,
            })

    beliefs: list[dict[str, Any]] = []
    raw_narrative = runtime.get("narrative", ())
    if isinstance(raw_narrative, (list, tuple)):
        for index, item in enumerate(raw_narrative[:64]):
            if not isinstance(item, Mapping):
                continue
            belief_id = str(item.get("capability_id") or item.get("id") or f"belief.{index}")
            uncertainty = item.get("uncertainty")
            try:
                certainty = max(0.0, min(1.0, 1.0 - float(uncertainty)))
            except (TypeError, ValueError):
                certainty = 0.5
            beliefs.append({
                "id": belief_id,
                "title": str(item.get("summary") or belief_id),
                "certainty": certainty,
                "evidence": int(item.get("evidence_gathered", 0) or 0),
                "contested": bool(item.get("contested", False)),
                "dissent": item.get("dissent") is not None,
            })

    activation_classes: dict[str, int] = {}
    raw_activations = cognition.get("activations")
    if isinstance(raw_activations, Mapping):
        for key, value in raw_activations.items():
            try:
                activation_classes[str(key)] = max(
                    0, min(15, int(round(abs(float(value)) * 15.0)))
                )
            except (TypeError, ValueError):
                continue

    prediction_errors: dict[str, str] = {}
    raw_errors = cognition.get("prediction_errors")
    if isinstance(raw_errors, (list, tuple)):
        for item in raw_errors:
            if not isinstance(item, Mapping):
                continue
            target = str(item.get("target_id") or item.get("predictor_id") or "")
            if target:
                prediction_errors[target] = _prediction_class(item.get("error"))

    mind_cognition = {
        "readouts": dict(cognition.get("readouts") or {}),
        "activationClasses": activation_classes,
        "predictionErrors": prediction_errors,
        "topologyHealth": str(cognition.get("topology_health") or "germinal"),
        "safetyState": {
            "frozen": bool(cognition.get("frozen", False)),
            "recovering": bool(cognition.get("recovering", False)),
            "consecutiveFailures": int(cognition.get("consecutive_failures", 0) or 0),
        },
        "strandedConcepts": list(cognition.get("stranded_concepts") or []),
        "predictiveGain": float(cognition.get("predictive_gain", 0.0) or 0.0),
        "representationMaturity": dict(cognition.get("representation_maturity") or {}),
        "topologyRevision": int(cognition.get("topology_revision", 0) or 0),
    }

    mind_topology = None
    if topology is not None:
        nodes = []
        for item in topology.get("nodes", ()) or ():
            if isinstance(item, Mapping):
                nodes.append({
                    "id": str(item.get("node_id") or item.get("id") or ""),
                    "kind": str(item.get("kind") or "concept"),
                })
        edges = []
        for item in topology.get("edges", ()) or ():
            if isinstance(item, Mapping):
                edges.append({
                    "sourceId": str(item.get("source_id") or item.get("sourceId") or ""),
                    "targetId": str(item.get("target_id") or item.get("targetId") or ""),
                    "kind": str(item.get("kind") or "excitatory"),
                })
        mind_topology = {"nodes": nodes, "edges": edges}

    metabolism = post.get("metabolism")
    if not isinstance(metabolism, Mapping):
        metabolism = None

    development = runtime.get("development")
    if not isinstance(development, Mapping):
        development = None

    sensory_phenotype = runtime.get("sensory_phenotype")
    if not isinstance(sensory_phenotype, Mapping):
        sensory_phenotype = None

    physiology = post.get("physiology")
    if not isinstance(physiology, Mapping):
        physiology = None

    return {
        "tick": int(rich_state.get("tick", 0) or 0),
        "display_id": str(rich_state.get("organism_id") or "physics3d"),
        "organism_state": physiology,
        "senses": senses,
        "beliefs": beliefs,
        "cognition": mind_cognition,
        "topology": mind_topology,
        "body_schema": rich_state.get("body_schema"),
        "sensory_phenotype": sensory_phenotype,
        "metabolism": metabolism,
        "development": development,
        "sampling": {
            "active": len(senses),
            "probing": 0,
        },
        "details": {
            "investigatedCapability": runtime.get("investigated_capability"),
            "evidenceGathered": int(runtime.get("evidence_gathered", 0) or 0),
            "homeostaticDeviation": float(runtime.get("homeostatic_deviation", 0.0) or 0.0),
        },
    }


def stream_runtime_mind_snapshot(
    stream: OrganismStream,
    rich_state: Mapping[str, Any],
) -> None:
    """Publish the full passive Physics3D mind projection on the canonical stream."""
    snapshot = _mind_snapshot_from_rich_state(rich_state)
    stream.push({
        "type": "mind_snapshot",
        "source": "physics3d",
        "tick": snapshot["tick"],
        "organism_id": rich_state.get("organism_id"),
        "snapshot": snapshot,
    })
