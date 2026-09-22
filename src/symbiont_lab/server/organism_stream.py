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
    result: dict[str, Any] = {}
    if tick.get("source") is not None:
        result["source"] = str(tick["source"])
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


def _copy_number(
    target: dict[str, Any],
    source: Mapping[str, Any],
    source_key: str,
    *,
    target_key: str | None = None,
    cast: type[int] | type[float] = float,
) -> None:
    """Copy a numeric observation only when the producer actually supplied it."""
    value = source.get(source_key)
    if value is None:
        return
    try:
        target[target_key or source_key] = cast(value)
    except (TypeError, ValueError):
        return


def _copy_bool(
    target: dict[str, Any],
    source: Mapping[str, Any],
    source_key: str,
    *,
    target_key: str | None = None,
) -> None:
    """Copy a boolean observation without converting absence into False."""
    value = source.get(source_key)
    if isinstance(value, bool):
        target[target_key or source_key] = value


def stream_runtime_tick(stream: OrganismStream, tick: Mapping[str, Any]) -> None:
    """Project one canonical runtime tick without fabricating absent observations."""
    if not isinstance(tick, Mapping):
        raise TypeError("tick must be a mapping")

    identity = _identity(tick)

    body: dict[str, Any] = {**identity, "type": "body"}
    _copy_number(body, tick, "tick", cast=int)
    if isinstance(tick.get("base_position"), (list, tuple)):
        try:
            body["base_position"] = [float(v) for v in tick["base_position"]]
        except (TypeError, ValueError):
            pass
    if isinstance(tick.get("base_orientation"), (list, tuple)):
        try:
            body["base_orientation"] = [float(v) for v in tick["base_orientation"]]
        except (TypeError, ValueError):
            pass
    if isinstance(tick.get("joints"), (list, tuple)):
        joints: list[dict[str, Any]] = []
        for item in tick["joints"]:
            if not isinstance(item, Mapping):
                continue
            joint: dict[str, Any] = {}
            if item.get("name") is not None:
                joint["name"] = str(item["name"])
            if item.get("position") is not None:
                try:
                    joint["position"] = float(item["position"])
                except (TypeError, ValueError):
                    pass
            if joint:
                joints.append(joint)
        body["joints"] = joints
    _copy_number(body, tick, "contact_count", cast=int)
    if tick.get("metabolic_reserve_ratio") is not None:
        _copy_number(body, tick, "metabolic_reserve_ratio", target_key="metabolic_reserve")
    elif tick.get("metabolic_reserve") is not None:
        _copy_number(body, tick, "metabolic_reserve")

    cognition: dict[str, Any] = {**identity, "type": "cognition"}
    _copy_number(cognition, tick, "tick", cast=int)
    _copy_number(cognition, tick, "schema_confidence")
    _copy_number(cognition, tick, "schema_parts", cast=int)
    _copy_number(cognition, tick, "schema_sensory_parts", cast=int)
    _copy_number(cognition, tick, "schema_cognitive_regions", cast=int)
    if tick.get("motor_origin") is not None:
        cognition["motor_origin"] = str(tick["motor_origin"])
    if tick.get("motor_origin_detail") is not None:
        cognition["motor_origin_detail"] = str(tick["motor_origin_detail"])
    _copy_number(cognition, tick, "predictor_count", cast=int)
    _copy_number(cognition, tick, "sensorimotor_patterns", cast=int)
    _copy_number(cognition, tick, "motor_primitives", cast=int)
    _copy_number(cognition, tick, "cognitive_motor_primitives", cast=int)
    if "prediction_error" in tick:
        cognition["prediction_error"] = tick.get("prediction_error")
    _copy_bool(cognition, tick, "slm_active")
    if "slm_models" in tick:
        cognition["slm_models"] = tick.get("slm_models")
    _copy_bool(cognition, tick, "prospective_selected")
    if "prospective_expected_value" in tick:
        cognition["prospective_expected_value"] = tick.get("prospective_expected_value")

    vitals: dict[str, Any] = {**identity, "type": "vitals"}
    _copy_number(vitals, tick, "tick", cast=int)
    _copy_bool(vitals, tick, "alive")
    _copy_number(vitals, tick, "joint_motion")
    _copy_number(vitals, tick, "resource_progress")
    _copy_number(vitals, tick, "displacement_from_origin")
    _copy_number(vitals, tick, "mechanical_work_joules")
    _copy_number(vitals, tick, "metabolic_work_cost")

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
            belief: dict[str, Any] = {
                "id": belief_id,
                "title": str(item.get("summary") or belief_id),
            }
            uncertainty = item.get("uncertainty")
            if uncertainty is not None:
                try:
                    belief["certainty"] = max(0.0, min(1.0, 1.0 - float(uncertainty)))
                except (TypeError, ValueError):
                    pass
            if item.get("evidence_gathered") is not None:
                try:
                    belief["evidence"] = int(item["evidence_gathered"])
                except (TypeError, ValueError):
                    pass
            if isinstance(item.get("contested"), bool):
                belief["contested"] = item["contested"]
            if "dissent" in item:
                belief["dissent"] = item.get("dissent") is not None
            beliefs.append(belief)

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

    mind_cognition: dict[str, Any] = {}
    if isinstance(cognition.get("readouts"), Mapping):
        mind_cognition["readouts"] = dict(cognition["readouts"])
    if cognition.get("topology_health") is not None:
        mind_cognition["topologyHealth"] = str(cognition["topology_health"])
    safety_state: dict[str, Any] = {}
    if isinstance(cognition.get("frozen"), bool):
        safety_state["frozen"] = cognition["frozen"]
    if isinstance(cognition.get("recovering"), bool):
        safety_state["recovering"] = cognition["recovering"]
    if cognition.get("consecutive_failures") is not None:
        try:
            safety_state["consecutiveFailures"] = int(cognition["consecutive_failures"])
        except (TypeError, ValueError):
            pass
    if safety_state:
        mind_cognition["safetyState"] = safety_state
    if isinstance(cognition.get("stranded_concepts"), (list, tuple)):
        mind_cognition["strandedConcepts"] = list(cognition["stranded_concepts"])
    if cognition.get("predictive_gain") is not None:
        try:
            mind_cognition["predictiveGain"] = float(cognition["predictive_gain"])
        except (TypeError, ValueError):
            pass
    if isinstance(cognition.get("representation_maturity"), Mapping):
        mind_cognition["representationMaturity"] = dict(cognition["representation_maturity"])
    if cognition.get("topology_revision") is not None:
        try:
            mind_cognition["topologyRevision"] = int(cognition["topology_revision"])
        except (TypeError, ValueError):
            pass

    observer_analysis = {
        "activationClasses": activation_classes,
        "predictionErrors": prediction_errors,
        "derivation": {
            "activationClasses": "observer quantization of absolute activation into 0..15",
            "predictionErrors": "observer classification of numeric prediction error",
        },
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

    snapshot: dict[str, Any] = {
        "senses": senses,
        "beliefs": beliefs,
        "cognition": mind_cognition,
        "topology": mind_topology,
        "body_schema": rich_state.get("body_schema"),
        "sensory_phenotype": sensory_phenotype,
        "metabolism": metabolism,
        "development": development,
        "observer_analysis": observer_analysis,
        "provenance": {
            "organismFacts": [
                "organism_state",
                "senses",
                "beliefs",
                "cognition",
                "topology",
                "body_schema",
                "sensory_phenotype",
                "metabolism",
                "development",
            ],
            "observerDerived": [
                "observer_analysis.activationClasses",
                "observer_analysis.predictionErrors",
            ],
        },
    }
    if rich_state.get("tick") is not None:
        try:
            snapshot["tick"] = int(rich_state["tick"])
        except (TypeError, ValueError):
            pass
    if rich_state.get("organism_id") is not None:
        snapshot["display_id"] = str(rich_state["organism_id"])
    if physiology is not None:
        snapshot["organism_state"] = physiology

    sampling: dict[str, Any] = {}
    if senses:
        sampling["active"] = len(senses)
    if sampling:
        snapshot["sampling"] = sampling

    details: dict[str, Any] = {}
    if runtime.get("investigated_capability") is not None:
        details["investigatedCapability"] = runtime["investigated_capability"]
    if runtime.get("evidence_gathered") is not None:
        try:
            details["evidenceGathered"] = int(runtime["evidence_gathered"])
        except (TypeError, ValueError):
            pass
    if runtime.get("homeostatic_deviation") is not None:
        try:
            details["homeostaticDeviation"] = float(runtime["homeostatic_deviation"])
        except (TypeError, ValueError):
            pass
    if details:
        snapshot["details"] = details
    return snapshot


def stream_runtime_mind_snapshot(
    stream: OrganismStream,
    rich_state: Mapping[str, Any],
) -> None:
    """Publish the full passive Physics3D mind projection on the canonical stream."""
    snapshot = _mind_snapshot_from_rich_state(rich_state)
    stream.push({
        "type": "mind_snapshot",
        "source": "physics3d",
        "tick": snapshot.get("tick"),
        "organism_id": rich_state.get("organism_id"),
        "snapshot": snapshot,
    })
