"""Unified passive Physics3D viewer.

PyBullet remains in the parent process as the physical apparatus. This module
runs one Tkinter window in a separate process and receives bounded evaluator
snapshots plus RGB camera frames. It can only send camera/viewer lifecycle
commands back to the parent; there is no control path into cognition.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from multiprocessing.context import BaseContext
from pathlib import Path
import os
import queue
import signal
import time
from typing import Mapping
from collections.abc import Sequence

from .humanoid import (
    BODY_KIND,
    BODY_STATE_SCHEMA_VERSION,
    CARRIER_MASS,
    JOINT_LIMITS,
    JOINT_SPECS,
    JOINT_TOPOLOGY,
    SEGMENTS,
)

HUMANOID_LINK_MASSES = tuple(
    SEGMENTS[topology.child_link].mass
    if topology.child_link in SEGMENTS
    else CARRIER_MASS
    for topology in JOINT_TOPOLOGY
)
HUMANOID_BASE_MASS = SEGMENTS["pelvis"].mass
HUMANOID_TOTAL_MASS = HUMANOID_BASE_MASS + sum(HUMANOID_LINK_MASSES)

_UNIT_CIRCLE_18 = tuple(
    (math.cos(math.radians(deg)), math.sin(math.radians(deg)))
    for deg in range(0, 360, 18)
)
_UNIT_CIRCLE_24 = tuple(
    (math.cos(math.radians(deg)), math.sin(math.radians(deg)))
    for deg in range(0, 360, 24)
)


def _convex_hull_2d(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Compute 2D convex hull via Monotone Chain algorithm."""
    unique_pts = sorted(set(points))
    if len(unique_pts) <= 2:
        return list(unique_pts)

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in unique_pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0.0:
            lower.pop()
        lower.append(p)

    upper: list[tuple[float, float]] = []
    for p in reversed(unique_pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0.0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def _point_in_polygon_2d(point: tuple[float, float], poly: Sequence[tuple[float, float]]) -> bool:
    """Ray casting point-in-polygon containment test."""
    if len(poly) < 3:
        return False
    x, y = point
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside



@dataclass(frozen=True, slots=True)
class MonitorSnapshot:
    tick: int
    symbiont_id: str
    embodiment_mode: str
    schema_confidence: float
    schema_parts: int
    schema_sensory_parts: int
    schema_cognitive_regions: int
    schema_dependency_evidence: int
    schema_dependencies: int
    predictor_count: int
    shadow_prediction_count: int
    promotable_shadow_count: int
    prediction_error: float | None
    active_effectors: int
    joint_motion: float
    contact_count: int
    mechanical_work_joules: float
    metabolic_work_cost: float
    height: float
    checkpoint_age: int
    symbiont_file: str
    strongest_outputs: tuple[tuple[str, float], ...]
    slm_records: int
    slm_transition_records: int
    slm_models: int
    slm_active: bool
    slm_training: bool
    slm_error: str | None
    slm_gate_reason: str | None
    slm_gate_gain: float | None
    slm_best_baseline: str | None
    slm_candidate_loss: float | None
    slm_best_baseline_loss: float | None
    cycle_ms: float
    realtime_ratio: float
    organism_ms: float
    physics_ms: float
    diagnostics_ms: float
    resource_distance: float
    resource_field: float
    resource_remaining: float
    absorbed_energy: float
    metabolic_reserve_ratio: float
    displacement_from_origin: float
    motor_origin: str
    initial_resource_distance: float
    minimum_resource_distance: float
    resource_progress: float
    motor_origin_cognition: int
    motor_origin_babbling: int
    motor_origin_primitive: int
    motor_origin_mixed: int
    motor_origin_spontaneous: int
    motor_origin_probe: int
    motor_origin_none: int
    motor_repertoire_size: int
    sensorimotor_coverage: float
    sensorimotor_patterns: int
    motor_primitives: int
    cognitive_motor_primitives: int
    best_motor_controllability: float
    best_motor_directional_consistency: float
    primitive_replay_active: bool
    sensorimotor_h1_samples: int
    sensorimotor_h4_samples: int
    sensorimotor_h16_samples: int
    sensorimotor_h64_samples: int
    passive_baseline_samples: int


@dataclass(frozen=True, slots=True)
class CameraState:
    yaw: float = 38.0
    pitch: float = -20.0
    distance: float = 3.1
    target_z: float = 0.85

    def bounded(self) -> "CameraState":
        return CameraState(
            yaw=float(self.yaw) % 360.0,
            pitch=max(-85.0, min(35.0, float(self.pitch))),
            distance=max(1.1, min(8.0, float(self.distance))),
            target_z=max(0.0, min(2.5, float(self.target_z))),
        )


def strongest_outputs(
    activations: Mapping[str, float],
    *,
    limit: int = 6,
) -> tuple[tuple[str, float], ...]:
    return tuple(
        sorted(
            ((str(channel), float(value)) for channel, value in activations.items()),
            key=lambda item: (-abs(item[1]), item[0]),
        )[:limit]
    )


def _event_transition(
    previous: Mapping[str, object] | None,
    current: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    """Return passive, evidence-backed events between two evaluator snapshots."""
    if previous is None:
        return ()
    tick = int(current.get("tick", 0))
    events: list[dict[str, object]] = []

    prev_origin = str(previous.get("motor_origin", "none"))
    cur_origin = str(current.get("motor_origin", "none"))
    if cur_origin != prev_origin:
        events.append({
            "tick": tick,
            "kind": "motor_origin",
            "category": "behavior",
            "label": f"Origen motor: {prev_origin} → {cur_origin}",
        })

    prev_min = float(previous.get("minimum_resource_distance", float("inf")))
    cur_min = float(current.get("minimum_resource_distance", prev_min))
    if cur_min + 0.01 < prev_min:
        events.append({
            "tick": tick,
            "kind": "resource_minimum",
            "category": "environment",
            "label": f"Nuevo mínimo al recurso: {cur_min:.3f} m",
        })

    prev_abs = float(previous.get("absorbed_energy", 0.0))
    cur_abs = float(current.get("absorbed_energy", prev_abs))
    if cur_abs > prev_abs + 1e-9:
        events.append({
            "tick": tick,
            "kind": "energy_absorbed",
            "category": "survival",
            "label": f"Energía absorbida: +{cur_abs - prev_abs:.3f}",
        })

    for field, kind, noun in (
        ("motor_primitives", "motor_primitive", "Primitiva motora"),
        ("cognitive_motor_primitives", "cognitive_primitive", "Primitiva cognitiva"),
        ("schema_parts", "schema_part", "Parte BodySchema"),
        ("predictor_count", "predictor", "Predictor activo"),
    ):
        before = int(previous.get(field, 0))
        after = int(current.get(field, before))
        if after > before:
            category = "learning" if kind in {
                "motor_primitive",
                "cognitive_primitive",
                "predictor",
            } else "body"
            events.append({
                "tick": tick,
                "kind": kind,
                "category": category,
                "label": f"{noun}: {before} → {after}",
            })

    prev_disp = float(previous.get("displacement_from_origin", 0.0))
    cur_disp = float(current.get("displacement_from_origin", prev_disp))
    for threshold in (0.05, 0.25, 0.50, 1.00):
        if prev_disp < threshold <= cur_disp:
            events.append({
                "tick": tick,
                "kind": "displacement_milestone",
                "category": "body",
                "label": f"Desplazamiento supera {threshold:.2f} m",
            })

    return tuple(events)


def _event_context(
    records: list[Mapping[str, object]],
    index: int,
    *,
    radius: int = 12,
) -> dict[str, object]:
    """Summarize observable changes around one event without inferring causality."""
    if not records:
        return {}
    index = max(0, min(len(records) - 1, int(index)))
    before = records[max(0, index - radius):index]
    after = records[index + 1:min(len(records), index + radius + 1)]

    def mean(field: str, sample: list[Mapping[str, object]]) -> float | None:
        values: list[float] = []
        for record in sample:
            value = record.get(field)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        return None if not values else sum(values) / len(values)

    def control(sample: list[Mapping[str, object]]) -> float | None:
        values: list[float] = []
        for record in sample:
            try:
                controllability = max(
                    0.0, float(record.get("best_motor_controllability", 0.0))
                )
                direction = max(
                    0.0,
                    float(record.get("best_motor_directional_consistency", 0.0)),
                )
            except (TypeError, ValueError):
                continue
            values.append((controllability * direction) ** 0.5)
        return None if not values else sum(values) / len(values)

    metrics: dict[str, tuple[float | None, float | None]] = {
        "movement": (mean("joint_motion", before), mean("joint_motion", after)),
        "control": (control(before), control(after)),
        "resource": (
            mean("resource_distance", before),
            mean("resource_distance", after),
        ),
        "energy": (
            mean("metabolic_reserve_ratio", before),
            mean("metabolic_reserve_ratio", after),
        ),
        "prediction_error": (
            mean("prediction_error", before),
            mean("prediction_error", after),
        ),
    }
    return {
        "tick": int(records[index].get("tick", index)),
        "radius": int(radius),
        "before_samples": len(before),
        "after_samples": len(after),
        "metrics": metrics,
    }


def _put_latest(target_queue, payload: dict) -> None:
    """Keep producers non-blocking by discarding stale UI messages."""
    try:
        target_queue.put_nowait(payload)
        return
    except queue.Full:
        pass
    try:
        target_queue.get_nowait()
    except queue.Empty:
        pass
    try:
        target_queue.put_nowait(payload)
    except queue.Full:
        pass


class UnifiedViewerProcess:
    """One-window passive evaluator with integrated 3D camera image."""

    def __init__(self, context: BaseContext) -> None:
        self._frames = context.Queue(maxsize=2)
        self._commands = context.Queue(maxsize=16)
        self._pending_commands: list[dict] = []
        self._started = False
        self._process = context.Process(
            target=_viewer_main,
            args=(self._frames, self._commands),
            daemon=True,
            name="symbiont-3d-viewer",
        )

    def start(self) -> None:
        self._started = True
        self._process.start()

    @property
    def is_alive(self) -> bool:
        return self._process.is_alive()

    def poll_commands(self) -> list[dict]:
        commands = list(self._pending_commands)
        self._pending_commands.clear()
        if self._started and not self._process.is_alive():
            commands.append({"type": "stop"})
        while True:
            try:
                commands.append(self._commands.get_nowait())
            except queue.Empty:
                break
        return commands

    def poll_stop(self) -> bool:
        stop = self._started and not self._process.is_alive()
        cmds = self.poll_commands()
        remaining = []
        for cmd in cmds:
            if cmd.get("type") == "stop":
                stop = True
            else:
                remaining.append(cmd)
        self._pending_commands.extend(remaining)
        return stop

    def publish(
        self,
        snapshot: MonitorSnapshot,
        *,
        physical_state: dict[str, object],
    ) -> None:
        if not self._process.is_alive():
            return
        _put_latest(
            self._frames,
            {
                "type": "frame",
                "snapshot": asdict(snapshot),
                "physical_state": physical_state,
            },
        )

    def close(self) -> None:
        if self._process.is_alive():
            _put_latest(self._frames, {"type": "close"})
            self._process.join(timeout=1.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)


# Backward-compatible name for callers/tests that still import MonitorProcess.
MonitorProcess = UnifiedViewerProcess


def snapshot_to_physical_state(record: Mapping[str, object]) -> dict[str, object]:
    """Reconstruct an evaluator-safe physical state payload from telemetry."""
    reconstructed_fields: list[str] = []
    joints = record.get("joints")
    if not joints or not isinstance(joints, (list, tuple)):
        reconstructed_fields.append("joints")
        joints = [
            {
                "joint_index": j_id,
                "position": 0.0,
                "velocity": 0.0,
                "applied_torque": 0.0,
            }
            for j_id in sorted(JOINT_LIMITS)
        ]
    contact_links = record.get("contact_links", ())
    base_pos = record.get("base_position", (0.0, 0.0, 0.9))
    base_orient = record.get("base_orientation", (0.0, 0.0, 0.0, 1.0))
    res_info = record.get("locomotion_resource")
    if isinstance(res_info, dict):
        res_pos = res_info.get("position", (float(base_pos[0]) + 3.0, float(base_pos[1]), 0.15))
        res_rem = float(res_info.get("remaining", 200.0))
    else:
        reconstructed_fields.append("resource_position")
        res_dist = float(record.get("resource_distance", 3.0))
        res_rem = float(record.get("resource_remaining", 200.0))
        res_pos = (float(base_pos[0]) + res_dist, float(base_pos[1]), 0.15)
    return {
        "_reconstructed_fields": reconstructed_fields,
        "schema_version": BODY_STATE_SCHEMA_VERSION,
        "body_kind": BODY_KIND,
        "base_position": list(base_pos),
        "base_orientation": list(base_orient),
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "joints": list(joints),
        "contact_links": list(contact_links),
        "locomotion_resource": {
            "position": list(res_pos),
            "remaining": res_rem,
        },
    }


def record_to_snapshot(
    record: Mapping[str, object],
    *,
    fallback_id: str = "subject:replay",
) -> dict[str, object]:
    """Extract a dictionary compatible with apply_snapshot from telemetry."""
    snap = dict(record)
    symb_id = record.get("symbiont_id") or record.get("organism_id") or fallback_id
    snap.setdefault("symbiont_id", symb_id)
    snap.setdefault("embodiment_mode", "replay")
    snap.setdefault("checkpoint_age", 0)
    snap.setdefault("realtime_ratio", 1.0)
    cycle = (
        float(record.get("organism_ms", 0.0))
        + float(record.get("physics_ms", 0.0))
        + float(record.get("diagnostics_ms", 0.0))
    )
    snap.setdefault("cycle_ms", cycle if cycle > 0 else 12.0)
    base_pos = record.get("base_position")
    snap.setdefault(
        "height",
        base_pos[2]
        if isinstance(base_pos, (list, tuple)) and len(base_pos) >= 3
        else 0.9,
    )
    snap.setdefault("strongest_outputs", ())
    snap.setdefault("slm_models", record.get("slm_models", 0))
    snap.setdefault("slm_active", record.get("slm_active", False))
    snap.setdefault("slm_training", False)
    snap.setdefault("slm_error", None)
    snap.setdefault("slm_gate_reason", None)
    snap.setdefault("slm_gate_gain", None)
    snap.setdefault("slm_best_baseline", None)
    snap.setdefault("slm_candidate_loss", None)
    snap.setdefault("slm_best_baseline_loss", None)
    snap.setdefault("symbiont_file", "")
    return snap


try:
    import tkinter as _tk

    class PillFrame(_tk.Frame):
        """Frame wrapping a text pill that properly delegates fg and bg options."""

        def __init__(
            self,
            parent: _tk.Misc,
            text_var: _tk.StringVar,
            fg_color: str,
            bg_color: str,
            *,
            border: str = "#30363d",
            **kwargs,
        ) -> None:
            super().__init__(
                parent,
                bg=bg_color,
                padx=8,
                pady=3,
                highlightthickness=1,
                highlightbackground=border,
                **kwargs,
            )
            self.label = _tk.Label(
                self,
                textvariable=text_var,
                bg=bg_color,
                fg=fg_color,
                font=("TkDefaultFont", 8, "bold"),
            )
            self.label.pack()

        def configure(self, cnf=None, **kw):
            if cnf is None and not kw:
                return super().configure()
            options = dict(cnf or {})
            options.update(kw)
            label_opts = {}
            if "fg" in options:
                label_opts["fg"] = options.pop("fg")
            if "foreground" in options:
                label_opts["foreground"] = options.pop("foreground")
            if "bg" in options:
                label_opts["bg"] = options["bg"]
            if label_opts:
                self.label.configure(**label_opts)
            if options:
                return super().configure(**options)
            return None

        config = configure

        def cget(self, key: str):
            if key in ("fg", "foreground"):
                return self.label.cget(key)
            return super().cget(key)

        __getitem__ = cget
except ImportError:
    PillFrame = None  # type: ignore[assignment,misc]


def _viewer_main(
    frame_queue=None,
    command_queue=None,
    *,
    replay_records: list[dict] | None = None,
    replay_file: str = "",
) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        os.nice(10)
    except OSError:
        pass
    try:
        import tkinter as tk
        from tkinter import ttk
        from PIL import Image, ImageDraw, ImageTk
        import numpy as np
        import pybullet as p
        from .humanoid import HumanoidPhysics
        from .resource import PhysicalResource
    except ImportError:
        print(
            "Physics3D unified viewer unavailable: install tkinter and "
            "the physics3d extra (Pillow)."
        )
        return

    # Palette: Modern dark Mission Control
    bg = "#0d1117"
    panel = "#161b22"
    border = "#30363d"
    sub_bg = "#21262d"
    fg = "#f0f6fc"
    muted = "#8b949e"
    cyan = "#38bdf8"
    orange = "#fb923c"
    green = "#34d399"
    red = "#f87171"
    blue = "#60a5fa"
    purple = "#a78bfa"
    yellow = "#facc15"

    is_replay = replay_records is not None

    root = tk.Tk()
    root.title(
        "Symbiont 3D · Mission Control (Replay)"
        if is_replay
        else "Symbiont 3D · Mission Control"
    )
    root.geometry("1560x920")
    root.minsize(1200, 720)
    root.configure(bg=bg)

    render_client = p.connect(p.DIRECT)
    if render_client < 0:
        raise RuntimeError("unified viewer could not create passive PyBullet renderer")
    preferred_renderer = p.ER_TINY_RENDERER
    try:
        test_view = p.computeViewMatrixFromYawPitchRoll((0.0, 0.0, 0.0), 2.0, 0.0, -20.0, 0.0, 2)
        test_proj = p.computeProjectionMatrixFOV(60.0, 1.0, 0.1, 10.0)
        test_img = p.getCameraImage(
            16,
            16,
            viewMatrix=test_view,
            projectionMatrix=test_proj,
            renderer=p.ER_BULLET_HARDWARE_OPENGL,
            flags=p.ER_NO_SEGMENTATION_MASK,
            physicsClientId=render_client,
        )
        if len(test_img[2]) > 0:
            preferred_renderer = p.ER_BULLET_HARDWARE_OPENGL
    except Exception:
        preferred_renderer = p.ER_TINY_RENDERER

    p.setGravity(0.0, 0.0, -9.81, physicsClientId=render_client)
    plane_shape = p.createCollisionShape(
        p.GEOM_PLANE,
        planeNormal=(0.0, 0.0, 1.0),
        physicsClientId=render_client,
    )
    p.createMultiBody(
        baseMass=0.0,
        baseCollisionShapeIndex=plane_shape,
        physicsClientId=render_client,
    )
    render_body = HumanoidPhysics(p, render_client)
    render_resource = PhysicalResource(p, render_client)

    # Grid setup for root: Header, Workspace, Bottom Panel
    root.grid_rowconfigure(0, weight=0)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=0)
    root.grid_columnconfigure(0, weight=1)

    # -------------------------------------------------------------
    # 1. TOP HEADER (Row 0)
    # -------------------------------------------------------------
    header_frame = tk.Frame(root, bg=panel, padx=14, pady=8, highlightthickness=1, highlightbackground=border)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1)

    title_box = tk.Frame(header_frame, bg=panel)
    title_box.grid(row=0, column=0, sticky="w")
    tk.Label(
        title_box,
        text="SYMBIONT 3D",
        bg=panel,
        fg=cyan,
        font=("TkDefaultFont", 12, "bold"),
    ).pack(side="left")
    tk.Label(
        title_box,
        text=" · MISSION CONTROL (REPLAY)" if is_replay else " · MISSION CONTROL",
        bg=panel,
        fg=fg,
        font=("TkDefaultFont", 12, "bold"),
    ).pack(side="left")

    initial_id = (
        f"{Path(replay_file).name if replay_file else 'telemetry'} · {len(replay_records):,} ticks grabados"
        if is_replay
        else "esperando simulación..."
    )
    identity_var = tk.StringVar(value=initial_id)
    tk.Label(
        title_box,
        textvariable=identity_var,
        bg=panel,
        fg=muted,
        font=("TkDefaultFont", 8),
        padx=12,
    ).pack(side="left")

    header_status_box = tk.Frame(header_frame, bg=panel)
    header_status_box.grid(row=0, column=2, sticky="e")

    def make_pill(parent, text_var, fg_color, bg_color):
        f = PillFrame(parent, text_var, fg_color, bg_color, border=border)
        f.pack(side="left", padx=4)
        return f

    tick_pill_var = tk.StringVar(value="TICK: 0")
    make_pill(header_status_box, tick_pill_var, fg, sub_bg)

    realtime_pill_var = tk.StringVar(value="1.00x")
    make_pill(header_status_box, realtime_pill_var, cyan, sub_bg)

    status_pill_var = tk.StringVar(value="● REPLAY" if is_replay else "● VIVO")
    make_pill(
        header_status_box,
        status_pill_var,
        "#ffffff",
        "#2563eb" if is_replay else "#15803d",
    )

    provenance_pill_var = tk.StringVar(value="GRABADO" if is_replay else "DIRECTO")
    provenance_pill = make_pill(
        header_status_box,
        provenance_pill_var,
        muted,
        sub_bg,
    )

    sim_state_pill_var = tk.StringVar(value="PAUSADO" if is_replay else "EJECUTANDO")
    sim_pill_frame = make_pill(header_status_box, sim_state_pill_var, cyan, "#1e293b")

    # -------------------------------------------------------------
    # 2. MAIN WORKSPACE (Row 1: Left - Center - Right)
    # -------------------------------------------------------------
    workspace = tk.Frame(root, bg=bg)
    workspace.grid(row=1, column=0, sticky="nsew")
    workspace.grid_rowconfigure(0, weight=1)
    workspace.grid_columnconfigure(0, minsize=0, weight=0)
    workspace.grid_columnconfigure(1, weight=1)
    workspace.grid_columnconfigure(2, minsize=0, weight=0)

    # -------------------------------------------------------------
    # LEFT PANEL: ANATOMY & ACTUATION
    # -------------------------------------------------------------
    left_panel = tk.Frame(workspace, bg=panel, padx=10, pady=8, highlightthickness=1, highlightbackground=border)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

    tk.Label(
        left_panel,
        text="ANATOMÍA Y ACTUACIÓN",
        bg=panel,
        fg=cyan,
        font=("TkDefaultFont", 9, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 6))

    # Section: Contact Sensors
    tk.Label(
        left_panel,
        text="CONTACTOS MECÁNICOS (SUELO)",
        bg=panel,
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(4, 2))

    contacts_frame = tk.Frame(left_panel, bg=sub_bg, padx=6, pady=6, highlightthickness=1, highlightbackground=border)
    contacts_frame.pack(fill="x", pady=(0, 8))

    contact_labels: dict[int, tk.Label] = {}
    contact_specs = [
        (-1, "Pelvis", 0, 0, 2),
        (11, "Mano Izq.", 1, 0, 1),
        (18, "Mano Der.", 1, 1, 1),
        (24, "Pie Izq.", 2, 0, 1),
        (30, "Pie Der.", 2, 1, 1),
    ]
    for link_id, name, row, col, span in contact_specs:
        cell = tk.Frame(contacts_frame, bg=sub_bg, padx=3, pady=2)
        cell.grid(row=row, column=col, columnspan=span, sticky="ew", padx=2, pady=2)
        contacts_frame.grid_columnconfigure(col, weight=1)
        tk.Label(
            cell,
            text=name,
            bg=sub_bg,
            fg=muted,
            font=("TkDefaultFont", 7),
        ).pack(side="left")
        lbl = tk.Label(
            cell,
            text="LIBRE",
            bg="#1b222d",
            fg="#6e7681",
            font=("TkDefaultFont", 7, "bold"),
            padx=4,
            pady=1,
            relief="flat",
        )
        lbl.pack(side="right")
        contact_labels[link_id] = lbl

    # Section: Joint Torques
    tk.Label(
        left_panel,
        text="TORQUES ARTICULARES (-1..+1)",
        bg=panel,
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(4, 2))

    torques_frame = tk.Frame(left_panel, bg=sub_bg, padx=6, pady=6, highlightthickness=1, highlightbackground=border)
    torques_frame.pack(fill="x", pady=(0, 8))

    joint_names = {
        index: spec.name.replace("_", " ").title()
        for index, spec in enumerate(JOINT_SPECS)
    }
    joint_canvases: dict[int, tk.Canvas] = {}
    joint_val_vars: dict[int, tk.StringVar] = {}

    for row_idx, (j_id, j_name) in enumerate(joint_names.items()):
        row_f = tk.Frame(torques_frame, bg=sub_bg)
        row_f.pack(fill="x", pady=2)
        tk.Label(
            row_f,
            text=j_name,
            bg=sub_bg,
            fg=fg,
            width=11,
            anchor="w",
            font=("TkDefaultFont", 8),
        ).pack(side="left")
        cv = tk.Canvas(row_f, width=120, height=13, bg="#0d1117", highlightthickness=1, highlightbackground=border)
        cv.pack(side="left", padx=4)
        cv.create_line(60, 0, 60, 13, fill="#30363d")
        bar_id = cv.create_rectangle(60, 2, 60, 11, fill=cyan, width=0)
        joint_canvases[j_id] = (cv, bar_id)
        val_v = tk.StringVar(value=" 0.00")
        joint_val_vars[j_id] = val_v
        tk.Label(
            row_f,
            textvariable=val_v,
            bg=sub_bg,
            fg=cyan,
            width=5,
            anchor="e",
            font=("TkFixedFont", 8, "bold"),
        ).pack(side="right")

    # Section: Active Opaque Effectors
    tk.Label(
        left_panel,
        text="SALIDAS MOTORAS ACTIVAS",
        bg=panel,
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(4, 2))

    outputs_var = tk.StringVar(value="Sin actividad motora")
    tk.Label(
        left_panel,
        textvariable=outputs_var,
        bg=sub_bg,
        fg=cyan,
        font=("TkFixedFont", 8),
        justify="left",
        anchor="nw",
        padx=6,
        pady=6,
        highlightthickness=1,
        highlightbackground=border,
    ).pack(fill="x", pady=(0, 8))

    # Section: Mechanical Metrics
    mech_frame = tk.Frame(left_panel, bg=sub_bg, padx=6, pady=6, highlightthickness=1, highlightbackground=border)
    mech_frame.pack(fill="x", pady=(0, 4))
    mech_vars = {}
    for r_idx, (k, lbl_text) in enumerate((
        ("height", "Altura Base"),
        ("motion", "Movimiento Articular"),
        ("work", "Trabajo Mecánico"),
        ("cost", "Coste Metabólico"),
    )):
        tk.Label(mech_frame, text=lbl_text, bg=sub_bg, fg=muted, font=("TkDefaultFont", 7), anchor="w").grid(row=r_idx, column=0, sticky="w", pady=1)
        v = tk.StringVar(value="—")
        mech_vars[k] = v
        tk.Label(mech_frame, textvariable=v, bg=sub_bg, fg=fg, font=("TkDefaultFont", 8, "bold"), anchor="e").grid(row=r_idx, column=1, sticky="e", pady=1)
    mech_frame.grid_columnconfigure(1, weight=1)

    # -------------------------------------------------------------
    # CENTER PANEL: 3D VIEWPORT & HUD OVERLAYS
    # -------------------------------------------------------------
    center_panel = tk.Frame(workspace, bg="#090d11")
    center_panel.grid(row=0, column=1, sticky="nsew")
    center_panel.grid_rowconfigure(3, weight=1)
    center_panel.grid_columnconfigure(0, weight=1)

    # Top HUD overlay banner
    hud_top = tk.Frame(center_panel, bg="#090d11", padx=8, pady=6)
    hud_top.grid(row=0, column=0, sticky="ew")
    hud_top.grid_columnconfigure(1, weight=1)

    motor_origin_badge = tk.Label(
        hud_top,
        text="ORIGEN: BABBLING",
        bg="#0891b2",
        fg="#ffffff",
        font=("TkDefaultFont", 8, "bold"),
        padx=10,
        pady=3,
        relief="flat",
    )
    motor_origin_badge.grid(row=0, column=0, sticky="w")

    resource_hud_badge = tk.Label(
        hud_top,
        text="RECURSO: — · PROGRESO: —",
        bg=panel,
        fg=fg,
        font=("TkDefaultFont", 8, "bold"),
        padx=10,
        pady=3,
        highlightthickness=1,
        highlightbackground=border,
    )
    resource_hud_badge.grid(row=0, column=2, sticky="e")

    # Situational overview: human-readable state before technical metrics.
    situation_strip = tk.Frame(
        center_panel,
        bg=panel,
        padx=8,
        pady=6,
        highlightthickness=1,
        highlightbackground=border,
    )
    situation_strip.grid(row=1, column=0, sticky="ew")
    for col in range(4):
        situation_strip.grid_columnconfigure(col, weight=1)

    situation_vars = {
        "behavior": tk.StringVar(value="MOVIMIENTO · —"),
        "learning": tk.StringVar(value="APRENDIZAJE · —"),
        "energy": tk.StringVar(value="ENERGÍA · —"),
        "goal": tk.StringVar(value="RECURSO · —"),
    }
    situation_labels: dict[str, tk.Label] = {}
    for col, (key, var) in enumerate(situation_vars.items()):
        lbl = tk.Label(
            situation_strip,
            textvariable=var,
            bg=sub_bg,
            fg=fg,
            font=("TkDefaultFont", 8, "bold"),
            padx=8,
            pady=5,
            highlightthickness=1,
            highlightbackground=border,
            cursor="hand2",
        )
        lbl.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 3, 0))
        situation_labels[key] = lbl

    behavior_detail_vars = {
        "activity": tk.StringVar(value="ACTIVIDAD · —"),
        "control": tk.StringVar(value="CONTROL MOTOR · —"),
        "locomotion": tk.StringVar(value="LOCOMOCIÓN · —"),
    }
    for col, (key, var) in enumerate(behavior_detail_vars.items()):
        lbl = tk.Label(
            situation_strip,
            textvariable=var,
            bg=panel,
            fg=muted,
            font=("TkDefaultFont", 7, "bold"),
            padx=8,
            pady=3,
        )
        lbl.grid(
            row=1,
            column=col if col < 2 else 2,
            columnspan=1 if col < 2 else 2,
            sticky="ew",
            padx=(0 if col == 0 else 3, 0),
            pady=(4, 0),
        )

    latest_event_var = tk.StringVar(value="EVENTOS · sin hitos todavía")
    latest_event_label = tk.Label(
        center_panel,
        textvariable=latest_event_var,
        bg="#101820",
        fg=muted,
        font=("TkDefaultFont", 7, "bold"),
        anchor="w",
        padx=10,
        pady=4,
        cursor="hand2",
    )
    latest_event_label.grid(row=2, column=0, sticky="ew")

    # 3D Scene Label
    scene_panel = tk.Frame(center_panel, bg="#090d11")
    scene_panel.grid(row=3, column=0, sticky="nsew")
    scene_panel.grid_rowconfigure(0, weight=1)
    scene_panel.grid_columnconfigure(0, weight=1)

    scene_label = tk.Label(
        scene_panel,
        bg="#090d11",
        fg=muted,
        text="esperando primer frame 3D...",
        anchor="center",
    )
    scene_label.grid(row=0, column=0, sticky="nsew")

    # -------------------------------------------------------------
    # 3D CAMERA STATE & CONTROLS HUD
    # -------------------------------------------------------------
    camera = CameraState()
    pan_offset = [0.0, 0.0]
    smooth_pos = [0.0, 0.0]
    overlay_visibility = {
        "grid": True,
        "com": True,
        "support": True,
        "velocity": True,
        "torques": True,
        "field": True,
        "trajectory": True,
        "compass": True,
        "shadow": True,
    }

    # Bottom Camera & Controls HUD
    hud_bottom = tk.Frame(center_panel, bg="#090d11", padx=8, pady=6)
    hud_bottom.grid(row=4, column=0, sticky="ew")

    cam_top_row = tk.Frame(hud_bottom, bg="#090d11")
    cam_top_row.pack(fill="x", pady=(0, 4))

    camera_btn_frame = tk.Frame(cam_top_row, bg="#090d11")
    camera_btn_frame.pack(side="left")

    def reset_camera() -> None:
        nonlocal camera
        pan_offset[0] = 0.0
        pan_offset[1] = 0.0
        camera = CameraState(38.0, -20.0, 3.1, 0.85)
        rerender_latest()

    def make_cam_btn(text, cam_target):
        def _set():
            nonlocal camera
            camera = cam_target.bounded()
            rerender_latest()
        b = tk.Button(
            camera_btn_frame,
            text=text,
            bg=sub_bg,
            fg=fg,
            activebackground="#30363d",
            activeforeground=fg,
            font=("TkDefaultFont", 7),
            padx=6,
            pady=2,
            relief="flat",
            command=_set,
        )
        b.pack(side="left", padx=2)
        return b

    make_cam_btn("🎥 3D", CameraState(38.0, -20.0, 3.1, 0.85))
    make_cam_btn("⬇ Cenital", CameraState(0.0, -84.0, 4.2, 0.0))
    make_cam_btn("👤 Frontal", CameraState(0.0, -10.0, 3.2, 0.85))
    make_cam_btn("➡️ Lateral", CameraState(90.0, -10.0, 3.2, 0.85))
    make_cam_btn("🌱 Recurso", CameraState(220.0, -18.0, 4.2, 0.50))
    make_cam_btn("🔍 Zoom", CameraState(38.0, -15.0, 1.8, 0.85))

    tk.Button(
        camera_btn_frame,
        text="🎯 Seguir",
        bg=sub_bg,
        fg=cyan,
        activebackground="#30363d",
        activeforeground=cyan,
        font=("TkDefaultFont", 7, "bold"),
        padx=6,
        pady=2,
        relief="flat",
        command=reset_camera,
    ).pack(side="left", padx=2)

    tk.Label(
        cam_top_row,
        text="Arrastre izq: Orbitar · Arrastre der/Shift: Pan · Rueda: Zoom · Doble clic: Seguir",
        bg="#090d11",
        fg=muted,
        font=("TkDefaultFont", 7),
    ).pack(side="right")

    layers_row = tk.Frame(hud_bottom, bg="#090d11")
    layers_row.pack(fill="x")

    tk.Label(
        layers_row,
        text="Capas:",
        bg="#090d11",
        fg=muted,
        font=("TkDefaultFont", 7, "bold"),
    ).pack(side="left", padx=(0, 4))

    layer_buttons: dict[str, tk.Button] = {}

    def make_layer_toggle(key: str, label: str) -> tk.Button:
        def _toggle() -> None:
            overlay_visibility[key] = not overlay_visibility[key]
            active = overlay_visibility[key]
            btn.configure(
                bg="#1e293b" if active else "#0d1117",
                fg=cyan if active else muted,
            )
            rerender_latest()

        btn = tk.Button(
            layers_row,
            text=label,
            bg="#1e293b" if overlay_visibility[key] else "#0d1117",
            fg=cyan if overlay_visibility[key] else muted,
            activebackground="#30363d",
            activeforeground=fg,
            font=("TkDefaultFont", 7),
            padx=5,
            pady=1,
            relief="flat",
            command=_toggle,
        )
        btn.pack(side="left", padx=2)
        layer_buttons[key] = btn
        return btn

    make_layer_toggle("grid", "🌐 Cuadrícula")
    make_layer_toggle("com", "⚖️ CoM")
    make_layer_toggle("support", "👣 Soporte/Huellas")
    make_layer_toggle("velocity", "➡️ Velocidad")
    make_layer_toggle("torques", "⚡ Torques")
    make_layer_toggle("field", "🎯 Campo Recurso")
    make_layer_toggle("trajectory", "📈 Trayectoria")
    make_layer_toggle("compass", "🧭 Brújula")

    # -------------------------------------------------------------
    # RIGHT PANEL: COGNITION, ECOLOGY & PRIVATE SLM
    # -------------------------------------------------------------
    right_panel = tk.Frame(workspace, bg=panel, padx=10, pady=8, highlightthickness=1, highlightbackground=border)
    right_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 0))

    def make_card(parent, title, accent_color):
        card = tk.Frame(parent, bg=sub_bg, padx=8, pady=6, highlightthickness=1, highlightbackground=border)
        card.pack(fill="x", pady=(0, 8))
        tk.Label(card, text=title, bg=sub_bg, fg=accent_color, font=("TkDefaultFont", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        content = tk.Frame(card, bg=sub_bg)
        content.pack(fill="x")
        content.grid_columnconfigure(1, weight=1)
        return content

    # Card 1: Cognition & BodySchema
    cog_content = make_card(right_panel, "COGNICIÓN & BODY SCHEMA", cyan)
    schema_bar_canvas = tk.Canvas(cog_content, width=280, height=8, bg="#0d1117", highlightthickness=0)
    schema_bar_canvas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    schema_bar_rect = schema_bar_canvas.create_rectangle(0, 0, 0, 8, fill=green, width=0)

    cog_vars = {}
    for r_i, (k, l_txt) in enumerate((
        ("schema", "Confianza BodySchema"),
        ("parts", "Partes / Senses"),
        ("regions", "Regiones / Evidencias"),
        ("predictors", "Predictores Activos"),
        ("shadows", "Sombras / Promocionables"),
        ("error", "Error Predicción"),
    ), start=1):
        tk.Label(cog_content, text=l_txt, bg=sub_bg, fg=muted, font=("TkDefaultFont", 7), anchor="w").grid(row=r_i, column=0, sticky="w", pady=1)
        v = tk.StringVar(value="—")
        cog_vars[k] = v
        tk.Label(cog_content, textvariable=v, bg=sub_bg, fg=fg, font=("TkDefaultFont", 8, "bold"), anchor="e").grid(row=r_i, column=1, sticky="e", pady=1)

    # Card 2: Ecology & Locomotion
    eco_content = make_card(right_panel, "ECOLOGÍA & METABOLISMO", green)
    reserve_bar_canvas = tk.Canvas(eco_content, width=280, height=8, bg="#0d1117", highlightthickness=0)
    reserve_bar_canvas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    reserve_bar_rect = reserve_bar_canvas.create_rectangle(0, 0, 0, 8, fill=green, width=0)

    eco_vars = {}
    for r_i, (k, l_txt) in enumerate((
        ("reserve", "Reserva / Absorbido"),
        ("distance", "Distancia Recurso"),
        ("progress", "Progreso Neto"),
        ("displacement", "Desplazamiento Origen"),
        ("repertoire", "Repertorio / Cobertura"),
        ("primitives", "Primitivas / Cognitivas"),
        ("control", "Control / Dirección"),
        ("origins", "Orígenes C/B/P/M/S"),
    ), start=1):
        tk.Label(eco_content, text=l_txt, bg=sub_bg, fg=muted, font=("TkDefaultFont", 7), anchor="w").grid(row=r_i, column=0, sticky="w", pady=1)
        v = tk.StringVar(value="—")
        eco_vars[k] = v
        tk.Label(eco_content, textvariable=v, bg=sub_bg, fg=fg, font=("TkDefaultFont", 8, "bold"), anchor="e").grid(row=r_i, column=1, sticky="e", pady=1)

    # Card 3: Private SLM
    slm_content = make_card(right_panel, "PRIVATE SLM (WORLD MODEL)", purple)
    slm_vars = {}
    for r_i, (k, l_txt) in enumerate((
        ("records", "Experiencias / Transiciones"),
        ("state", "Estado Modelo"),
        ("gate", "Última Puerta"),
        ("loss", "Pérdida Modelo / Baseline"),
    )):
        tk.Label(slm_content, text=l_txt, bg=sub_bg, fg=muted, font=("TkDefaultFont", 7), anchor="w").grid(row=r_i, column=0, sticky="w", pady=1)
        v = tk.StringVar(value="—")
        slm_vars[k] = v
        tk.Label(slm_content, textvariable=v, bg=sub_bg, fg=fg, font=("TkDefaultFont", 8, "bold"), anchor="e").grid(row=r_i, column=1, sticky="e", pady=1)

    # Deep-dive controls. The default view keeps the organism central; technical
    # panels are available on demand without removing any evaluator data.
    deepdive_box = tk.Frame(header_frame, bg=panel)
    deepdive_box.grid(row=0, column=1, sticky="e", padx=8)

    panel_visibility = {"body": False, "data": False, "timeline": False}

    def _set_toggle_style(button, active: bool) -> None:
        button.configure(
            bg=cyan if active else sub_bg,
            fg="#000000" if active else muted,
        )

    def toggle_body_panel() -> None:
        panel_visibility["body"] = not panel_visibility["body"]
        if panel_visibility["body"]:
            workspace.grid_columnconfigure(0, minsize=290)
            left_panel.grid()
        else:
            left_panel.grid_remove()
            workspace.grid_columnconfigure(0, minsize=0)
        _set_toggle_style(body_toggle_btn, panel_visibility["body"])

    def toggle_data_panel() -> None:
        panel_visibility["data"] = not panel_visibility["data"]
        if panel_visibility["data"]:
            workspace.grid_columnconfigure(2, minsize=350)
            right_panel.grid()
        else:
            right_panel.grid_remove()
            workspace.grid_columnconfigure(2, minsize=0)
        _set_toggle_style(data_toggle_btn, panel_visibility["data"])

    def toggle_timeline_panel() -> None:
        panel_visibility["timeline"] = not panel_visibility["timeline"]
        if panel_visibility["timeline"]:
            bottom_frame.grid()
        else:
            bottom_frame.grid_remove()
        _set_toggle_style(timeline_toggle_btn, panel_visibility["timeline"])

    def _deepdive_button(text, command):
        return tk.Button(
            deepdive_box,
            text=text,
            command=command,
            bg=sub_bg,
            fg=muted,
            activebackground=border,
            activeforeground=fg,
            font=("TkDefaultFont", 7, "bold"),
            padx=7,
            pady=2,
            relief="flat",
        )

    body_toggle_btn = _deepdive_button("CUERPO", toggle_body_panel)
    body_toggle_btn.pack(side="left", padx=2)
    data_toggle_btn = _deepdive_button("DATOS", toggle_data_panel)
    data_toggle_btn.pack(side="left", padx=2)
    timeline_toggle_btn = _deepdive_button("TIMELINE", toggle_timeline_panel)
    timeline_toggle_btn.pack(side="left", padx=2)
    events_toggle_btn = _deepdive_button("EVENTOS", toggle_timeline_panel)
    events_toggle_btn.pack(side="left", padx=2)

    situation_labels["behavior"].bind("<Button-1>", lambda _e: toggle_body_panel())
    situation_labels["learning"].bind("<Button-1>", lambda _e: toggle_data_panel())
    situation_labels["energy"].bind("<Button-1>", lambda _e: toggle_data_panel())
    situation_labels["goal"].bind("<Button-1>", lambda _e: toggle_data_panel())
    latest_event_label.bind("<Button-1>", lambda _e: toggle_timeline_panel())

    # -------------------------------------------------------------
    # 3. BOTTOM PANEL: TELEMETRY TIME-SERIES & CONTROLS (Row 2)
    # -------------------------------------------------------------
    bottom_frame = tk.Frame(root, bg=panel, padx=12, pady=6, highlightthickness=1, highlightbackground=border)
    bottom_frame.grid(row=2, column=0, sticky="ew")
    bottom_frame.grid_columnconfigure(0, weight=1)
    bottom_frame.grid_columnconfigure(1, minsize=320, weight=0)

    chart_box = tk.Frame(bottom_frame, bg=panel)
    chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    chart = tk.Canvas(chart_box, height=110, bg="#090d11", highlightthickness=1, highlightbackground=border)
    chart.pack(fill="both", expand=True)

    event_listbox = tk.Listbox(
        chart_box,
        height=4,
        bg="#0d1117",
        fg=fg,
        selectbackground="#1d4ed8",
        selectforeground="#ffffff",
        highlightthickness=1,
        highlightbackground=border,
        activestyle="none",
        font=("TkFixedFont", 7),
    )
    event_listbox.pack(fill="x", pady=(4, 0))

    event_context_var = tk.StringVar(
        value="Selecciona un evento para comparar el contexto antes/después."
    )
    event_context_label = tk.Label(
        chart_box,
        textvariable=event_context_var,
        bg="#101820",
        fg=muted,
        justify="left",
        anchor="w",
        font=("TkFixedFont", 7),
        padx=8,
        pady=5,
    )
    event_context_label.pack(fill="x", pady=(4, 0))

    ctrl_box = tk.Frame(bottom_frame, bg=sub_bg, padx=10, pady=8, highlightthickness=1, highlightbackground=border)
    ctrl_box.grid(row=0, column=1, sticky="nsew")

    # Overview is the default. Deep-dive panels remain fully available via header
    # toggles or by clicking a situational indicator.
    left_panel.grid_remove()
    right_panel.grid_remove()
    bottom_frame.grid_remove()

    timing_var = tk.StringVar(value="Ciclo: — · Checkpoint: —")

    event_log: list[dict[str, object]] = []
    previous_event_snapshot: dict[str, object] | None = None
    replay_event_index: list[tuple[int, dict[str, object]]] = []

    if is_replay:
        tk.Label(ctrl_box, text="CONTROL DE REPLAY", bg=sub_bg, fg=cyan, font=("TkDefaultFont", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 2))

        slider_var = tk.DoubleVar(value=0)
        is_scrubbing = False
        current_replay_idx = 0
        is_playing = False
        replay_speed = 1.0

        replay_event_index.clear()
        prev_record = None
        for replay_idx, replay_record in enumerate(replay_records or ()):
            for event in _event_transition(prev_record, replay_record):
                replay_event_index.append((replay_idx, dict(event)))
            prev_record = replay_record

        def on_slider_move(val):
            nonlocal current_replay_idx
            if is_scrubbing:
                return
            load_replay_tick(int(float(val)))

        replay_slider = tk.Scale(
            ctrl_box,
            from_=0,
            to=max(0, len(replay_records) - 1) if replay_records else 0,
            orient="horizontal",
            variable=slider_var,
            command=on_slider_move,
            bg=sub_bg,
            fg=fg,
            troughcolor="#0d1117",
            activebackground=cyan,
            highlightthickness=0,
            bd=0,
            showvalue=False,
            resolution=1,
        )
        replay_slider.pack(fill="x", pady=(0, 2))

        btn_row = tk.Frame(ctrl_box, bg=sub_bg)
        btn_row.pack(fill="x", pady=(2, 4))

        def goto_start():
            load_replay_tick(0)

        def goto_end():
            if replay_records:
                load_replay_tick(len(replay_records) - 1)

        def step_back():
            load_replay_tick(current_replay_idx - 1)

        def step_fwd():
            load_replay_tick(current_replay_idx + 1)

        def toggle_play():
            nonlocal is_playing
            is_playing = not is_playing
            if is_playing:
                play_btn.configure(text="⏸ Pausar", bg="#2563eb")
                sim_state_pill_var.set("REPRODUCIENDO")
                schedule_replay_step()
            else:
                play_btn.configure(text="▶ Reproducir", bg="#15803d")
                sim_state_pill_var.set("PAUSADO")

        tk.Button(btn_row, text="⟲", bg="#21262d", fg=fg, font=("TkDefaultFont", 7), padx=4, pady=2, relief="flat", command=goto_start).pack(side="left", padx=1)
        tk.Button(btn_row, text="⏮ -1", bg="#21262d", fg=fg, font=("TkDefaultFont", 7), padx=5, pady=2, relief="flat", command=step_back).pack(side="left", padx=1)
        play_btn = tk.Button(btn_row, text="▶ Reproducir", bg="#15803d", fg="#ffffff", font=("TkDefaultFont", 8, "bold"), padx=8, pady=2, relief="flat", command=toggle_play)
        play_btn.pack(side="left", padx=2)
        tk.Button(btn_row, text="+1 ⏭", bg="#21262d", fg=fg, font=("TkDefaultFont", 7), padx=5, pady=2, relief="flat", command=step_fwd).pack(side="left", padx=1)
        tk.Button(btn_row, text="⏭|", bg="#21262d", fg=fg, font=("TkDefaultFont", 7), padx=4, pady=2, relief="flat", command=goto_end).pack(side="left", padx=1)

        speed_row = tk.Frame(ctrl_box, bg=sub_bg)
        speed_row.pack(fill="x", pady=(0, 2))

        loop_var = tk.BooleanVar(value=True)
        loop_chk = tk.Checkbutton(
            speed_row,
            text="Bucle",
            variable=loop_var,
            bg=sub_bg,
            fg=muted,
            selectcolor="#0d1117",
            activebackground=sub_bg,
            activeforeground=fg,
            font=("TkDefaultFont", 7),
        )
        loop_chk.pack(side="left", padx=(0, 4))

        speed_buttons = []
        def set_replay_speed(mult, active_btn):
            nonlocal replay_speed
            replay_speed = mult
            for b in speed_buttons:
                b.configure(bg="#1c2430", fg=muted)
            active_btn.configure(bg=cyan, fg="#000000")

        for mult, lbl in ((0.5, "0.5x"), (1.0, "1x"), (2.0, "2x"), (5.0, "5x"), (20.0, "Max")):
            btn = tk.Button(
                speed_row,
                text=lbl,
                bg=cyan if mult == 1.0 else "#1c2430",
                fg="#000000" if mult == 1.0 else muted,
                font=("TkDefaultFont", 7, "bold" if mult == 1.0 else "normal"),
                padx=4,
                pady=1,
                relief="flat",
            )
            btn.configure(command=lambda m=mult, b=btn: set_replay_speed(m, b))
            btn.pack(side="left", padx=1)
            speed_buttons.append(btn)

        replay_info_var = tk.StringVar(value="")
        tk.Label(
            ctrl_box,
            textvariable=replay_info_var,
            bg=sub_bg,
            fg=muted,
            font=("TkDefaultFont", 7),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        def load_replay_tick(idx: int) -> None:
            nonlocal current_replay_idx, is_scrubbing, latest_physical_state
            if not replay_records:
                return
            current_replay_idx = max(0, min(len(replay_records) - 1, idx))
            is_scrubbing = True
            slider_var.set(current_replay_idx)
            is_scrubbing = False
            rec = replay_records[current_replay_idx]
            tick_no = rec.get("tick", current_replay_idx)
            replay_info_var.set(f"Tick {tick_no:,} ({current_replay_idx + 1:,} / {len(replay_records):,})")

            window_start = max(0, current_replay_idx - max_history + 1)
            prediction_history.clear()
            schema_history.clear()
            resource_dist_history.clear()
            resource_raw_history.clear()
            reserve_history.clear()
            tick_history.clear()
            event_log.clear()
            event_log.extend(
                event for event_idx, event in replay_event_index
                if event_idx <= current_replay_idx
            )
            refresh_event_list()
            # Rebuild history up to, but not including, the selected tick.
            # apply_snapshot appends the selected tick exactly once.
            for r in replay_records[window_start:current_replay_idx]:
                err = r.get("prediction_error")
                prediction_history.append(None if err is None else float(err))
                schema_history.append(float(r.get("schema_confidence", 0.0)))
                d = float(r.get("resource_distance", 0.0))
                initial_d = max(1e-9, float(r.get("initial_resource_distance", d or 1.0)))
                resource_dist_history.append(max(0.0, min(1.0, d / initial_d)))
                resource_raw_history.append(d)
                reserve_history.append(float(r.get("metabolic_reserve_ratio", 0.0)))
                tick_history.append(int(r.get("tick", 0)))

            p_state = snapshot_to_physical_state(rec)
            trajectory_history.clear()
            for historical in replay_records[max(0, current_replay_idx - max_trajectory + 1) : current_replay_idx + 1]:
                pos = historical.get("base_position")
                if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                    trajectory_history.append(
                        (float(pos[0]), float(pos[1]), float(pos[2]))
                    )
            snap = record_to_snapshot(
                rec,
                fallback_id=Path(replay_file).stem if replay_file else "subject:replay",
            )
            latest_physical_state = p_state
            render_scene(p_state)
            apply_snapshot(snap, p_state)

        def schedule_replay_step() -> None:
            if not is_playing or not replay_records:
                return
            next_idx = current_replay_idx + 1
            if next_idx >= len(replay_records):
                if loop_var.get():
                    next_idx = 0
                else:
                    toggle_play()
                    return
            load_replay_tick(next_idx)
            delay = max(10, int(1000.0 / (12.0 * max(0.1, replay_speed))))
            root.after(delay, schedule_replay_step)

        # Keyboard bindings for replay
        root.bind("<space>", lambda _e: toggle_play())
        root.bind("<Left>", lambda _e: step_back())
        root.bind(",", lambda _e: step_back())
        root.bind("<Right>", lambda _e: step_fwd())
        root.bind(".", lambda _e: step_fwd())
        root.bind("n", lambda _e: step_fwd())
        root.bind("<Home>", lambda _e: goto_start())
        root.bind("<End>", lambda _e: goto_end())
        root.bind("0", lambda _e: goto_start())
        root.bind("1", lambda _e: set_replay_speed(0.5, speed_buttons[0]))
        root.bind("2", lambda _e: set_replay_speed(1.0, speed_buttons[1]))
        root.bind("3", lambda _e: set_replay_speed(2.0, speed_buttons[2]))
        root.bind("4", lambda _e: set_replay_speed(5.0, speed_buttons[3]))
        root.bind("5", lambda _e: set_replay_speed(20.0, speed_buttons[4]))
        root.bind("r", lambda _e: reset_camera())

        def goto_selected_event(_event=None):
            selection = event_listbox.curselection()
            if not selection:
                return
            visible_events = event_log[-40:]
            selected = visible_events[int(selection[0])]
            selected_tick = int(selected["tick"])
            for replay_idx, event in replay_event_index:
                if int(event["tick"]) == selected_tick and event["label"] == selected["label"]:
                    show_event_context(
                        _event_context(replay_records, replay_idx, radius=12)
                    )
                    load_replay_tick(replay_idx)
                    return

        def preview_selected_event(_event=None):
            selection = event_listbox.curselection()
            if not selection:
                return
            visible_events = event_log[-40:]
            selected = visible_events[int(selection[0])]
            selected_tick = int(selected["tick"])
            for replay_idx, event in replay_event_index:
                if int(event["tick"]) == selected_tick and event["label"] == selected["label"]:
                    show_event_context(
                        _event_context(replay_records, replay_idx, radius=12)
                    )
                    return

        event_listbox.bind("<<ListboxSelect>>", preview_selected_event)
        event_listbox.bind("<Double-Button-1>", goto_selected_event)
        event_listbox.bind("<Return>", goto_selected_event)
    else:
        tk.Label(ctrl_box, text="CONTROL DE SIMULACIÓN", bg=sub_bg, fg=cyan, font=("TkDefaultFont", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 6))

        btn_row = tk.Frame(ctrl_box, bg=sub_bg)
        btn_row.pack(fill="x", pady=(0, 6))

        is_paused = False

        def toggle_pause():
            nonlocal is_paused
            is_paused = not is_paused
            if is_paused:
                pause_btn.configure(text="▶ Reanudar", bg="#15803d")
                sim_state_pill_var.set("⏸ PAUSADO")
                sim_pill_frame.configure(bg="#374151")
            else:
                pause_btn.configure(text="⏸ Pausar", bg="#2563eb")
                sim_state_pill_var.set("EJECUTANDO")
                sim_pill_frame.configure(bg="#1e293b")
            _put_latest(command_queue, {"type": "pause", "paused": is_paused})

        def step_single():
            _put_latest(command_queue, {"type": "step"})

        pause_btn = tk.Button(
            btn_row,
            text="⏸ Pausar",
            bg="#2563eb",
            fg="#ffffff",
            font=("TkDefaultFont", 8, "bold"),
            padx=10,
            pady=3,
            relief="flat",
            command=toggle_pause,
        )
        pause_btn.pack(side="left", padx=(0, 6))

        step_btn = tk.Button(
            btn_row,
            text="⏭ +1 Tick",
            bg="#374151",
            fg=fg,
            font=("TkDefaultFont", 8),
            padx=8,
            pady=3,
            relief="flat",
            command=step_single,
        )
        step_btn.pack(side="left")

        speed_row = tk.Frame(ctrl_box, bg=sub_bg)
        speed_row.pack(fill="x", pady=(0, 4))
        tk.Label(speed_row, text="Velocidad:", bg=sub_bg, fg=muted, font=("TkDefaultFont", 7)).pack(side="left", padx=(0, 4))

        speed_buttons = []

        def set_speed(multiplier, active_btn):
            for b in speed_buttons:
                b.configure(bg="#1c2430", fg=muted)
            active_btn.configure(bg=cyan, fg="#000000")
            _put_latest(command_queue, {"type": "speed", "speed": multiplier})

        for mult, lbl in ((0.5, "0.5x"), (1.0, "1x"), (2.0, "2x"), (10.0, "Max")):
            btn = tk.Button(
                speed_row,
                text=lbl,
                bg=cyan if mult == 1.0 else "#1c2430",
                fg="#000000" if mult == 1.0 else muted,
                font=("TkDefaultFont", 7, "bold" if mult == 1.0 else "normal"),
                padx=5,
                pady=1,
                relief="flat",
            )
            btn.configure(command=lambda m=mult, b=btn: set_speed(m, b))
            btn.pack(side="left", padx=2)
            speed_buttons.append(btn)

        tk.Label(
            ctrl_box,
            textvariable=timing_var,
            bg=sub_bg,
            fg=muted,
            font=("TkDefaultFont", 7),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        # Keyboard bindings
        root.bind("<space>", lambda _e: toggle_pause())
        root.bind(".", lambda _e: step_single())
        root.bind("n", lambda _e: step_single())
        root.bind("1", lambda _e: set_speed(0.5, speed_buttons[0]))
        root.bind("2", lambda _e: set_speed(1.0, speed_buttons[1]))
        root.bind("3", lambda _e: set_speed(2.0, speed_buttons[2]))
        root.bind("4", lambda _e: set_speed(10.0, speed_buttons[3]))
        root.bind("r", lambda _e: reset_camera())

        def preview_live_event(_event=None):
            selection = event_listbox.curselection()
            if not selection or not snapshot_history:
                return
            visible_events = event_log[-40:]
            selected = visible_events[int(selection[0])]
            target_tick = int(selected["tick"])
            best_idx = min(
                range(len(snapshot_history)),
                key=lambda idx: abs(
                    int(snapshot_history[idx].get("tick", idx)) - target_tick
                ),
            )
            show_event_context(
                _event_context(snapshot_history, best_idx, radius=12)
            )

        event_listbox.bind("<<ListboxSelect>>", preview_live_event)

    # -------------------------------------------------------------
    # 3D CAMERA & SCENE RENDER LOGIC
    # -------------------------------------------------------------
    drag_origin: tuple[int, int, float, float] | None = None
    pan_drag_origin: tuple[int, int, float, float] | None = None
    latest_physical_state: dict[str, object] | None = None
    render_pending = False
    photo_ref = None
    trajectory_history: list[tuple[float, float, float]] = []
    max_trajectory = 120
    footstep_history: list[tuple[float, float, float]] = []
    max_footsteps = 30

    def _project_world(
        position: tuple[float, float, float],
        *,
        view_matrix,
        projection_matrix,
        width: int,
        height: int,
    ) -> tuple[int, int] | None:
        v_m = np.asarray(view_matrix, dtype=float).reshape((4, 4), order="F")
        p_m = np.asarray(projection_matrix, dtype=float).reshape((4, 4), order="F")
        vp = p_m @ v_m
        x, y, z = float(position[0]), float(position[1]), float(position[2])
        cw = vp[3, 0] * x + vp[3, 1] * y + vp[3, 2] * z + vp[3, 3]
        if cw <= 1e-6:
            return None
        inv_w = 1.0 / cw
        nz = (vp[2, 0] * x + vp[2, 1] * y + vp[2, 2] * z + vp[2, 3]) * inv_w
        if nz < -1.0 or nz > 1.0:
            return None
        nx = (vp[0, 0] * x + vp[0, 1] * y + vp[0, 2] * z + vp[0, 3]) * inv_w
        ny = (vp[1, 0] * x + vp[1, 1] * y + vp[1, 2] * z + vp[1, 3]) * inv_w
        sx = int((nx + 1.0) * 0.5 * width)
        sy = int((1.0 - ny) * 0.5 * height)
        if sx < -30 or sx > width + 30 or sy < -30 or sy > height + 30:
            return None
        return sx, sy

    last_resource_pos: tuple[float, float, float] | None = None
    last_resource_alpha: float | None = None

    def render_scene(physical_state: dict[str, object]) -> None:
        nonlocal photo_ref, last_resource_pos, last_resource_alpha
        render_body.restore_physical_state(physical_state)
        resource_state = physical_state.get("locomotion_resource")
        if isinstance(resource_state, dict):
            position = resource_state.get("position")
            if isinstance(position, (list, tuple)) and len(position) == 3:
                pos_tup = (float(position[0]), float(position[1]), float(position[2]))
                if pos_tup != last_resource_pos:
                    p.resetBasePositionAndOrientation(
                        render_resource.body_id,
                        pos_tup,
                        (0.0, 0.0, 0.0, 1.0),
                        physicsClientId=render_client,
                    )
                    last_resource_pos = pos_tup
            remaining = float(resource_state.get("remaining", 0.0))
            alpha = 1.0 if remaining > 0.0 else 0.15
            if alpha != last_resource_alpha:
                p.changeVisualShape(
                    render_resource.body_id,
                    -1,
                    rgbaColor=(0.52, 0.78, 0.36, alpha),
                    physicsClientId=render_client,
                )
                last_resource_alpha = alpha
        width, height = 540, 360
        base_position, _ = p.getBasePositionAndOrientation(
            render_body.body_id,
            physicsClientId=render_client,
        )
        if smooth_pos[0] == 0.0 and smooth_pos[1] == 0.0:
            smooth_pos[0] = float(base_position[0])
            smooth_pos[1] = float(base_position[1])
        else:
            smooth_pos[0] = smooth_pos[0] * 0.85 + float(base_position[0]) * 0.15
            smooth_pos[1] = smooth_pos[1] * 0.85 + float(base_position[1]) * 0.15

        target = (
            float(smooth_pos[0] + pan_offset[0]),
            float(smooth_pos[1] + pan_offset[1]),
            float(camera.target_z),
        )
        view = p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=target,
            distance=camera.distance,
            yaw=camera.yaw,
            pitch=camera.pitch,
            roll=0.0,
            upAxisIndex=2,
        )
        projection = p.computeProjectionMatrixFOV(
            fov=55.0,
            aspect=width / height,
            nearVal=0.05,
            farVal=25.0,
        )

        # Precompute unified View-Projection matrix for high-speed scalar projection
        v_m = np.asarray(view, dtype=float).reshape((4, 4), order="F")
        p_m = np.asarray(projection, dtype=float).reshape((4, 4), order="F")
        vp = p_m @ v_m
        m00, m01, m02, m03 = float(vp[0, 0]), float(vp[0, 1]), float(vp[0, 2]), float(vp[0, 3])
        m10, m11, m12, m13 = float(vp[1, 0]), float(vp[1, 1]), float(vp[1, 2]), float(vp[1, 3])
        m20, m21, m22, m23 = float(vp[2, 0]), float(vp[2, 1]), float(vp[2, 2]), float(vp[2, 3])
        m30, m31, m32, m33 = float(vp[3, 0]), float(vp[3, 1]), float(vp[3, 2]), float(vp[3, 3])

        def _project(pos: tuple[float, float, float]) -> tuple[int, int] | None:
            x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
            cw = m30 * x + m31 * y + m32 * z + m33
            if cw <= 1e-6:
                return None
            inv_w = 1.0 / cw
            nz = (m20 * x + m21 * y + m22 * z + m23) * inv_w
            if nz < -1.0 or nz > 1.0:
                return None
            nx = (m00 * x + m01 * y + m02 * z + m03) * inv_w
            ny = (m10 * x + m11 * y + m12 * z + m13) * inv_w
            sx = int((nx + 1.0) * 0.5 * width)
            sy = int((1.0 - ny) * 0.5 * height)
            if sx < -30 or sx > width + 30 or sy < -30 or sy > height + 30:
                return None
            return sx, sy

        try:
            image_data = p.getCameraImage(
                width=width,
                height=height,
                viewMatrix=view,
                projectionMatrix=projection,
                renderer=preferred_renderer,
                flags=p.ER_NO_SEGMENTATION_MASK,
                physicsClientId=render_client,
            )
        except Exception:
            image_data = p.getCameraImage(
                width=width,
                height=height,
                viewMatrix=view,
                projectionMatrix=projection,
                renderer=p.ER_TINY_RENDERER,
                flags=p.ER_NO_SEGMENTATION_MASK,
                physicsClientId=render_client,
            )

        # High-performance C-level byte buffer unpacking
        image = Image.frombuffer("RGBA", (width, height), bytearray(image_data[2]), "raw", "RGBA", 0, 1)
        draw = ImageDraw.Draw(image, "RGBA")

        # ---------------------------------------------------------
        # 1. GROUND GRID & ORIGIN (Z=0)
        # ---------------------------------------------------------
        if overlay_visibility.get("grid", True):
            grid_cx = round(float(base_position[0]))
            grid_cy = round(float(base_position[1]))
            for x_val in range(grid_cx - 5, grid_cx + 6):
                p_start = _project((float(x_val), float(grid_cy - 5), 0.0))
                p_end = _project((float(x_val), float(grid_cy + 5), 0.0))
                if p_start is not None and p_end is not None:
                    draw.line([p_start, p_end], fill=(55, 68, 88, 65), width=1)
            for y_val in range(grid_cy - 5, grid_cy + 6):
                p_start = _project((float(grid_cx - 5), float(y_val), 0.0))
                p_end = _project((float(grid_cx + 5), float(y_val), 0.0))
                if p_start is not None and p_end is not None:
                    draw.line([p_start, p_end], fill=(55, 68, 88, 65), width=1)

            orig_c = _project((0.0, 0.0, 0.0))
            if orig_c is not None:
                ox, oy = orig_c
                draw.ellipse((ox - 4, oy - 4, ox + 4, oy + 4), fill=(148, 163, 184, 180))
                p_x = _project((0.6, 0.0, 0.0))
                p_y = _project((0.0, 0.6, 0.0))
                if p_x is not None:
                    draw.line([orig_c, p_x], fill=(239, 68, 68, 160), width=2)
                if p_y is not None:
                    draw.line([orig_c, p_y], fill=(34, 197, 94, 160), width=2)

        # ---------------------------------------------------------
        # 2. ECOLOGICAL RESOURCE FIELD & PULSE
        # ---------------------------------------------------------
        if overlay_visibility.get("field", True) and isinstance(resource_state, dict):
            r_pos = resource_state.get("position")
            if isinstance(r_pos, (list, tuple)) and len(r_pos) == 3:
                rx_w, ry_w, rz_w = float(r_pos[0]), float(r_pos[1]), float(r_pos[2])
                field_rad = float(resource_state.get("field_radius", 6.0))
                for r_val, r_alpha in ((field_rad, 55), (field_rad * 0.5, 75), (1.0, 110)):
                    ring_pts = []
                    for c_cos, c_sin in _UNIT_CIRCLE_18:
                        pt = _project((rx_w + r_val * c_cos, ry_w + r_val * c_sin, 0.0))
                        if pt is not None:
                            ring_pts.append(pt)
                    if len(ring_pts) >= 12:
                        ring_pts.append(ring_pts[0])
                        draw.line(ring_pts, fill=(52, 211, 153, r_alpha), width=1)

                dist_to_res = math.sqrt((float(base_position[0]) - rx_w) ** 2 + (float(base_position[1]) - ry_w) ** 2)
                rem_mat = float(resource_state.get("remaining", 0.0))
                if dist_to_res <= 0.65 and rem_mat > 0.0:
                    p_res = _project((rx_w, ry_w, rz_w))
                    p_base = _project((float(base_position[0]), float(base_position[1]), float(base_position[2])))
                    if p_res is not None and p_base is not None:
                        draw.line([p_res, p_base], fill=(74, 222, 128, 220), width=3)
                        rx_s, ry_s = p_res
                        draw.ellipse((rx_s - 14, ry_s - 14, rx_s + 14, ry_s + 14), outline=(74, 222, 128, 200), width=2)

        # ---------------------------------------------------------
        # 3. FAKE CONTACT SHADOW (Z=0 BLOB)
        # ---------------------------------------------------------
        if overlay_visibility.get("shadow", True):
            h_z = max(0.01, float(base_position[2]))
            if h_z < 2.5:
                rx_s = 0.22 * (1.0 + min(1.0, h_z * 0.4))
                ry_s = 0.16 * (1.0 + min(1.0, h_z * 0.4))
                s_alpha = max(15, int(130 * (1.0 - min(1.0, h_z / 2.0))))
                bx, by = float(base_position[0]), float(base_position[1])
                shadow_pts = []
                for c_cos, c_sin in _UNIT_CIRCLE_24:
                    pt = _project((bx + rx_s * c_cos, by + ry_s * c_sin, 0.0))
                    if pt is not None:
                        shadow_pts.append(pt)
                if len(shadow_pts) >= 6:
                    draw.polygon(shadow_pts, fill=(10, 15, 25, s_alpha))

        # ---------------------------------------------------------
        # 4. TRAJECTORY TRAIL
        # ---------------------------------------------------------
        if overlay_visibility.get("trajectory", True):
            projected_trail = [
                point
                for pos in trajectory_history
                if (point := _project(pos)) is not None
            ]
            if len(projected_trail) >= 2:
                draw.line(projected_trail, fill=(56, 189, 248, 150), width=3)
                sx, sy = projected_trail[0]
                draw.ellipse((sx - 4, sy - 4, sx + 4, sy + 4), fill=(139, 148, 158, 190))
                ex, ey = projected_trail[-1]
                draw.ellipse((ex - 5, ey - 5, ex + 5, ey + 5), fill=(56, 189, 248, 230))

        # ---------------------------------------------------------
        # 5. RESOURCE TARGET INDICATOR
        # ---------------------------------------------------------
        if isinstance(resource_state, dict):
            resource_position = resource_state.get("position")
            if isinstance(resource_position, (list, tuple)) and len(resource_position) == 3:
                projected_resource = _project(tuple(float(v) for v in resource_position))
                projected_base = _project(tuple(float(v) for v in base_position))
                if projected_resource is not None:
                    rx, ry = projected_resource
                    draw.ellipse(
                        (rx - 7, ry - 7, rx + 7, ry + 7),
                        outline=(52, 211, 153, 235),
                        width=3,
                    )
                    if projected_base is not None and overlay_visibility.get("field", True):
                        draw.line(
                            (projected_base[0], projected_base[1], rx, ry),
                            fill=(52, 211, 153, 75),
                            width=1,
                        )

        # ---------------------------------------------------------
        # 6. BATCH LINK STATES, CONTACTS & SUPPORT POLYGON
        # ---------------------------------------------------------
        all_link_states = p.getLinkStates(
            render_body.body_id,
            list(range(15)),
            computeForwardKinematics=True,
            physicsClientId=render_client,
        )

        contact_links = set(int(v) for v in physical_state.get("contact_links", ()))
        ground_contacts: list[tuple[float, float]] = []
        for link_id in contact_links:
            if link_id == -1:
                gx, gy = float(base_position[0]), float(base_position[1])
            elif 0 <= link_id < len(all_link_states):
                ls = all_link_states[link_id]
                gx, gy = float(ls[4][0]), float(ls[4][1])
            else:
                continue
            ground_contacts.append((gx, gy))
            if link_id in (11, 18, 24, 30, -1):
                footstep_history.append((gx, gy, 0.0))
        del footstep_history[:-max_footsteps]

        if overlay_visibility.get("support", True) and footstep_history:
            total_steps = len(footstep_history)
            for step_idx, step_pos in enumerate(footstep_history):
                step_proj = _project(step_pos)
                if step_proj is not None:
                    sx, sy = step_proj
                    alpha = int(35 + 165 * (step_idx / max(1, total_steps)))
                    draw.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=(52, 211, 153, alpha))

        # ---------------------------------------------------------
        # 7. CENTER OF MASS (CoM) & STABILITY POLYGON
        # ---------------------------------------------------------
        com_x = HUMANOID_BASE_MASS * float(base_position[0])
        com_y = HUMANOID_BASE_MASS * float(base_position[1])
        com_z = HUMANOID_BASE_MASS * float(base_position[2])
        for link_idx, mass in enumerate(HUMANOID_LINK_MASSES):
            if link_idx < len(all_link_states):
                ls = all_link_states[link_idx]
                com_x += mass * float(ls[0][0])
                com_y += mass * float(ls[0][1])
                com_z += mass * float(ls[0][2])

        com_3d = (com_x / HUMANOID_TOTAL_MASS, com_y / HUMANOID_TOTAL_MASS, com_z / HUMANOID_TOTAL_MASS)
        com_ground = (com_3d[0], com_3d[1], 0.0)

        hull = _convex_hull_2d(ground_contacts) if ground_contacts else []
        is_stable = _point_in_polygon_2d((com_ground[0], com_ground[1]), hull) if len(hull) >= 3 else False

        if overlay_visibility.get("support", True) and ground_contacts:
            poly_color = (52, 211, 153, 50) if is_stable else (251, 146, 60, 60)
            line_color = (52, 211, 153, 200) if is_stable else (251, 146, 60, 220)
            if len(hull) >= 3:
                proj_poly = [
                    pt
                    for pt in (_project((hx, hy, 0.0)) for hx, hy in hull)
                    if pt is not None
                ]
                if len(proj_poly) >= 3:
                    draw.polygon(proj_poly, fill=poly_color, outline=line_color)
            elif len(hull) == 2:
                p1 = _project((hull[0][0], hull[0][1], 0.0))
                p2 = _project((hull[1][0], hull[1][1], 0.0))
                if p1 is not None and p2 is not None:
                    draw.line([p1, p2], fill=line_color, width=2)

        if overlay_visibility.get("com", True):
            proj_com_3d = _project(com_3d)
            proj_com_ground = _project(com_ground)
            if proj_com_3d is not None and proj_com_ground is not None:
                draw.line([proj_com_3d, proj_com_ground], fill=(234, 179, 8, 160), width=1)
                cx3, cy3 = proj_com_3d
                draw.ellipse((cx3 - 3, cy3 - 3, cx3 + 3, cy3 + 3), fill=(250, 204, 21, 230))
            if proj_com_ground is not None:
                gx, gy = proj_com_ground
                com_color = (52, 211, 153, 240) if (len(ground_contacts) >= 3 and is_stable) else (239, 68, 68, 240)
                draw.ellipse((gx - 6, gy - 6, gx + 6, gy + 6), outline=com_color, width=2)
                draw.line((gx - 9, gy, gx + 9, gy), fill=com_color, width=1)
                draw.line((gx, gy - 9, gx, gy + 9), fill=com_color, width=1)

        # ---------------------------------------------------------
        # 8. LINEAR VELOCITY VECTOR
        # ---------------------------------------------------------
        if overlay_visibility.get("velocity", True):
            lin_vel = physical_state.get("linear_velocity")
            if isinstance(lin_vel, (list, tuple)) and len(lin_vel) >= 3:
                vx, vy, vz = float(lin_vel[0]), float(lin_vel[1]), float(lin_vel[2])
                speed = math.sqrt(vx * vx + vy * vy + vz * vz)
                if speed > 0.06:
                    bx, by, bz = float(base_position[0]), float(base_position[1]), float(base_position[2])
                    p_base = _project((bx, by, bz))
                    p_tip = _project((bx + vx * 0.45, by + vy * 0.45, bz + vz * 0.45))
                    if p_base is not None and p_tip is not None:
                        draw.line([p_base, p_tip], fill=(250, 204, 21, 230), width=2)
                        tx, ty = p_tip
                        bx_s, by_s = p_base
                        ang = math.atan2(ty - by_s, tx - bx_s)
                        ah1 = (tx - 8 * math.cos(ang - 0.5), ty - 8 * math.sin(ang - 0.5))
                        ah2 = (tx - 8 * math.cos(ang + 0.5), ty - 8 * math.sin(ang + 0.5))
                        draw.polygon([p_tip, ah1, ah2], fill=(250, 204, 21, 240))
                        draw.text((tx + 6, ty - 6), f"{speed:.2f} m/s", fill=(250, 204, 21, 220))

        # ---------------------------------------------------------
        # 9. CONTACT LINKS & COMMANDED JOINT TORQUES
        # ---------------------------------------------------------
        if overlay_visibility.get("torques", True):
            for link_id in contact_links:
                if link_id == -1:
                    world_pos = tuple(float(v) for v in base_position)
                elif 0 <= link_id < len(all_link_states):
                    world_pos = tuple(float(v) for v in all_link_states[link_id][4])
                else:
                    continue
                projected = _project(world_pos)
                if projected is not None:
                    cx, cy = projected
                    draw.ellipse(
                        (cx - 8, cy - 8, cx + 8, cy + 8),
                        outline=(52, 211, 153, 245),
                        width=3,
                    )

            for joint in physical_state.get("joints", ()):
                if not isinstance(joint, dict):
                    continue
                torque = float(joint.get("applied_torque", 0.0))
                if abs(torque) < 0.9:
                    continue
                joint_index = int(joint.get("joint_index", -1))
                if not (0 <= joint_index < len(all_link_states)):
                    continue
                world_pos = tuple(float(v) for v in all_link_states[joint_index][4])
                projected = _project(world_pos)
                if projected is not None:
                    jx, jy = projected
                    radius = 4 + int(min(8.0, abs(torque) / 3.0))
                    marker = (56, 189, 248, 210) if torque >= 0 else (251, 146, 60, 210)
                    draw.ellipse(
                        (jx - radius, jy - radius, jx + radius, jy + radius),
                        fill=marker,
                    )

        # ---------------------------------------------------------
        # 10. 3D ORIENTATION COMPASS GIZMO
        # ---------------------------------------------------------
        if overlay_visibility.get("compass", True):
            cx, cy = width - 42, 42
            draw.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=(15, 23, 42, 160), outline=(51, 65, 85, 180))
            axis_len = 20.0
            for axis_idx, (axis_color, axis_label) in enumerate([
                ((239, 68, 68, 240), "X"),
                ((34, 197, 94, 240), "Y"),
                ((59, 130, 246, 240), "Z"),
            ]):
                dx = v_m[0, axis_idx] * axis_len
                dy = -v_m[1, axis_idx] * axis_len
                tip_x, tip_y = int(cx + dx), int(cy + dy)
                draw.line([(cx, cy), (tip_x, tip_y)], fill=axis_color, width=2)
                draw.text((tip_x + (3 if dx >= 0 else -9), tip_y + (2 if dy >= 0 else -10)), axis_label, fill=axis_color)

        label_w = max(1, scene_label.winfo_width())
        label_h = max(1, scene_label.winfo_height())
        scale = min(label_w / width, label_h / height)
        if scale > 0 and abs(scale - 1.0) > 0.08:
            target_size = (
                max(1, int(width * scale)),
                max(1, int(height * scale)),
            )
            image = image.resize(target_size, Image.Resampling.NEAREST)
        photo_ref = ImageTk.PhotoImage(image)
        scene_label.configure(image=photo_ref, text="")

    def rerender_latest() -> None:
        nonlocal render_pending
        if latest_physical_state is None or render_pending:
            return
        render_pending = True

        def _do_render() -> None:
            nonlocal render_pending
            render_pending = False
            if latest_physical_state is not None:
                render_scene(latest_physical_state)

        root.after(30, _do_render)

    def on_press(event) -> None:
        nonlocal drag_origin
        drag_origin = (event.x, event.y, camera.yaw, camera.pitch)

    def on_drag(event) -> None:
        nonlocal camera
        if drag_origin is None:
            return
        x0, y0, yaw0, pitch0 = drag_origin
        camera = CameraState(
            yaw=yaw0 + (event.x - x0) * 0.35,
            pitch=pitch0 - (event.y - y0) * 0.30,
            distance=camera.distance,
            target_z=camera.target_z,
        ).bounded()
        rerender_latest()

    def on_pan_press(event) -> None:
        nonlocal pan_drag_origin
        pan_drag_origin = (event.x, event.y, pan_offset[0], pan_offset[1])

    def on_pan_drag(event) -> None:
        if pan_drag_origin is None:
            return
        x0, y0, px0, py0 = pan_drag_origin
        dx_mouse = event.x - x0
        dy_mouse = event.y - y0
        yaw_rad = math.radians(camera.yaw)
        scale = camera.distance * 0.0025
        pan_offset[0] = px0 - (dx_mouse * math.cos(yaw_rad) + dy_mouse * math.sin(yaw_rad)) * scale
        pan_offset[1] = py0 - (-dx_mouse * math.sin(yaw_rad) + dy_mouse * math.cos(yaw_rad)) * scale
        rerender_latest()

    def on_double_click(_event) -> None:
        pan_offset[0] = 0.0
        pan_offset[1] = 0.0
        rerender_latest()

    def on_wheel(event) -> None:
        nonlocal camera
        direction = 0
        if getattr(event, "delta", 0):
            direction = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        camera = CameraState(
            yaw=camera.yaw,
            pitch=camera.pitch,
            distance=camera.distance * (1.0 + 0.10 * direction),
            target_z=camera.target_z,
        ).bounded()
        rerender_latest()

    scene_label.bind("<ButtonPress-1>", on_press)
    scene_label.bind("<B1-Motion>", on_drag)
    scene_label.bind("<ButtonPress-3>", on_pan_press)
    scene_label.bind("<B3-Motion>", on_pan_drag)
    scene_label.bind("<Shift-ButtonPress-1>", on_pan_press)
    scene_label.bind("<Shift-B1-Motion>", on_pan_drag)
    scene_label.bind("<Double-Button-1>", on_double_click)
    scene_label.bind("<MouseWheel>", on_wheel)
    scene_label.bind("<Button-4>", on_wheel)
    scene_label.bind("<Button-5>", on_wheel)

    # -------------------------------------------------------------
    # TELEMETRY SERIES & MULTI-PARAM CHART
    # -------------------------------------------------------------
    prediction_history: list[float | None] = []
    schema_history: list[float] = []
    resource_dist_history: list[float] = []
    resource_raw_history: list[float] = []
    reserve_history: list[float] = []
    tick_history: list[int] = []
    snapshot_history: list[dict[str, object]] = []
    max_history = 180

    def refresh_event_list() -> None:
        event_listbox.delete(0, "end")
        for event in event_log[-40:]:
            category = str(event.get("category", "behavior"))
            event_listbox.insert(
                "end",
                f"{int(event['tick']):>8,}  [{event_category_labels.get(category, category.upper())}]  {event['label']}",
            )
        if event_log:
            event_listbox.see("end")
            last = event_log[-1]
            category = str(last.get("category", "behavior"))
            latest_event_var.set(
                f"{event_category_labels.get(category, 'EVENTO')} · tick {int(last['tick']):,} · {last['label']}"
            )
            latest_event_label.configure(
                fg=event_category_colors.get(category, muted)
            )

    def record_events(previous: Mapping[str, object] | None, current: Mapping[str, object]) -> None:
        for event in _event_transition(previous, current):
            event_log.append(dict(event))
        del event_log[:-200]
        if panel_visibility["timeline"] or event_log:
            refresh_event_list()

    def show_event_context(context: Mapping[str, object]) -> None:
        metrics = context.get("metrics", {})
        if not isinstance(metrics, Mapping):
            return

        def fmt_pair(name: str, label: str, suffix: str = "") -> str:
            pair = metrics.get(name)
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                return f"{label:<12} —"
            before, after = pair
            if before is None or after is None:
                return f"{label:<12} —"
            delta = float(after) - float(before)
            sign = "+" if delta >= 0 else ""
            return (
                f"{label:<12} {float(before):.3f} → {float(after):.3f} "
                f"({sign}{delta:.3f}{suffix})"
            )

        lines = [
            f"CONTEXTO ±{int(context.get('radius', 0))} ticks · asociación temporal, no causalidad",
            fmt_pair("movement", "Movimiento"),
            fmt_pair("control", "Control"),
            fmt_pair("resource", "Recurso", " m"),
            fmt_pair("energy", "Energía"),
            fmt_pair("prediction_error", "Error pred."),
        ]
        event_context_var.set("\n".join(lines))

    def draw_chart() -> None:
        chart.delete("all")
        width = max(1, chart.winfo_width())
        height = max(1, chart.winfo_height())
        pad_l, pad_r, pad_t, pad_b = 30, 20, 24, 18
        graph_w = max(1, width - pad_l - pad_r)
        graph_h = max(1, height - pad_t - pad_b)

        # Legend
        chart.create_text(pad_l, 10, text="LÍNEA TEMPORAL DE APRENDIZAJE", fill=muted, anchor="w", font=("TkDefaultFont", 7, "bold"))
        chart.create_oval(pad_l + 210, 8, pad_l + 218, 16, fill=orange, width=0)
        chart.create_text(pad_l + 224, 12, text="Error Predicción", fill=orange, anchor="w", font=("TkDefaultFont", 7))
        chart.create_oval(pad_l + 320, 8, pad_l + 328, 16, fill=green, width=0)
        chart.create_text(pad_l + 334, 12, text="Confianza BodySchema", fill=green, anchor="w", font=("TkDefaultFont", 7))
        chart.create_oval(pad_l + 470, 8, pad_l + 478, 16, fill=cyan, width=0)
        chart.create_text(pad_l + 484, 12, text="Distancia / Inicial", fill=cyan, anchor="w", font=("TkDefaultFont", 7))

        # Grid lines
        for step in (0.25, 0.50, 0.75, 1.00):
            y_grid = pad_t + graph_h * (1.0 - step)
            chart.create_line(pad_l, y_grid, pad_l + graph_w, y_grid, fill="#1c232d", dash=(2, 4))
        chart.create_line(pad_l, pad_t, pad_l, pad_t + graph_h, fill=border)
        chart.create_line(pad_l, pad_t + graph_h, pad_l + graph_w, pad_t + graph_h, fill=border)

        if event_log and tick_history:
            min_tick = int(tick_history[0])
            max_tick = int(tick_history[-1])
            span = max(1, max_tick - min_tick)
            for event in event_log[-80:]:
                tick = int(event["tick"])
                if tick < min_tick or tick > max_tick:
                    continue
                category = str(event.get("category", "behavior"))
                x = pad_l + graph_w * (tick - min_tick) / span
                color = event_category_colors.get(category, muted)
                chart.create_line(x, pad_t, x, pad_t + graph_h, fill=color, dash=(1, 4))
                chart.create_oval(x - 3, pad_t - 1, x + 3, pad_t + 5, fill=color, width=0)

        def series(values: list[float | None], color: str) -> None:
            if len(values) < 2:
                return
            segment: list[float] = []
            for index, value in enumerate(values):
                if value is None:
                    if len(segment) >= 4:
                        chart.create_line(*segment, fill=color, width=2)
                    segment = []
                    continue
                x = pad_l + graph_w * index / max(1, len(values) - 1)
                bounded = max(0.0, min(1.0, float(value)))
                y = pad_t + graph_h * (1.0 - bounded)
                segment.extend((x, y))
            if len(segment) >= 4:
                chart.create_line(*segment, fill=color, width=2)

        series(prediction_history, orange)
        series(schema_history, green)
        series(resource_dist_history, cyan)

        legend_y = height - 6
        x_legend = pad_l
        for category in ("body", "learning", "survival", "environment", "behavior"):
            color = event_category_colors[category]
            chart.create_oval(x_legend, legend_y - 3, x_legend + 6, legend_y + 3, fill=color, width=0)
            x_legend += 10
            chart.create_text(
                x_legend,
                legend_y,
                text=event_category_labels[category],
                fill=muted,
                anchor="w",
                font=("TkDefaultFont", 6),
            )
            x_legend += 58

    # -------------------------------------------------------------
    # SNAPSHOT UPDATE LOGIC
    # -------------------------------------------------------------
    event_category_colors = {
        "body": cyan,
        "learning": purple,
        "survival": green,
        "environment": yellow,
        "behavior": blue,
    }
    event_category_labels = {
        "body": "CUERPO",
        "learning": "APRENDIZAJE",
        "survival": "SUPERVIVENCIA",
        "environment": "ENTORNO",
        "behavior": "CONDUCTA",
    }

    motor_origin_colors = {
        "cognition": "#1d4ed8",
        "babbling": "#0891b2",
        "primitive": "#059669",
        "mixed": "#7c3aed",
        "spontaneous": "#d97706",
        "probe": "#0f766e",
        "none": "#374151",
    }

    def apply_snapshot(payload: dict, physical_state: dict, update_ui: bool = True) -> None:
        p_err = payload.get("prediction_error")
        conf = float(payload.get("schema_confidence", 0.0))
        dist = float(payload.get("resource_distance", 0.0))
        reserve = float(payload.get("metabolic_reserve_ratio", 0.0))

        # Update History. Every series keeps one slot per snapshot so
        # missing prediction errors cannot shift curves against one another.
        prediction_history.append(None if p_err is None else float(p_err))
        schema_history.append(conf)
        initial_dist = max(1e-9, float(payload.get("initial_resource_distance", dist or 1.0)))
        resource_dist_history.append(max(0.0, min(1.0, dist / initial_dist)))
        resource_raw_history.append(dist)
        reserve_history.append(reserve)
        tick_history.append(int(payload["tick"]))

        del prediction_history[:-max_history]
        del schema_history[:-max_history]
        del resource_dist_history[:-max_history]
        del resource_raw_history[:-max_history]
        del reserve_history[:-max_history]
        del tick_history[:-max_history]

        if not update_ui:
            return

        # Header
        identity_var.set(f"{payload['symbiont_id']}")
        tick_pill_var.set(f"TICK: {int(payload['tick']):,}")
        realtime_pill_var.set(f"{float(payload['realtime_ratio']):.2f}x")

        reconstructed = tuple(physical_state.get("_reconstructed_fields", ()))
        if is_replay and reconstructed:
            provenance_pill_var.set("RECONSTRUIDO")
            provenance_pill.configure(fg=yellow)
        elif is_replay:
            provenance_pill_var.set("GRABADO")
            provenance_pill.configure(fg=green)
        else:
            provenance_pill_var.set("DIRECTO")
            provenance_pill.configure(fg=muted)

        # Mechanical contacts
        active_contacts = set(physical_state.get("contact_links", ()))
        for link_id, lbl in contact_labels.items():
            if link_id in active_contacts:
                lbl.configure(bg="#15803d", fg="#ffffff", text="CONTACTO", relief="solid")
            else:
                lbl.configure(bg="#1b222d", fg="#6e7681", text="LIBRE", relief="flat")

        # Joint Torques & Meters
        joints_list = physical_state.get("joints", ())
        max_t = 18.0
        for j_item in joints_list:
            if not isinstance(j_item, dict):
                continue
            j_id = int(j_item.get("joint_index", -1))
            if j_id in joint_canvases:
                torque = float(j_item.get("applied_torque", 0.0))
                cv_item = joint_canvases[j_id]
                ratio = max(-1.0, min(1.0, torque / max_t))
                if isinstance(cv_item, tuple):
                    cv, bar_id = cv_item
                    if ratio > 0.02:
                        cv.coords(bar_id, 60, 2, 60 + int(ratio * 55), 11)
                        cv.itemconfigure(bar_id, fill=cyan)
                    elif ratio < -0.02:
                        cv.coords(bar_id, 60 - int(abs(ratio) * 55), 2, 60, 11)
                        cv.itemconfigure(bar_id, fill=orange)
                    else:
                        cv.coords(bar_id, 60, 2, 60, 11)
                else:
                    cv = cv_item
                    cv.delete("all")
                    cv.create_line(60, 0, 60, 13, fill="#30363d")
                    if ratio > 0.02:
                        cv.create_rectangle(60, 2, 60 + int(ratio * 55), 11, fill=cyan, width=0)
                    elif ratio < -0.02:
                        cv.create_rectangle(60 - int(abs(ratio) * 55), 2, 60, 11, fill=orange, width=0)
                val_str = f"{torque:+.1f}" if abs(torque) >= 0.05 else " 0.0"
                joint_val_vars[j_id].set(val_str)

        # Active Effectors
        strongest = payload.get("strongest_outputs", ())
        outputs_var.set(
            "\n".join(
                f"{str(ch):<8} {float(v):+.3f}"
                for ch, v in strongest
            ) or "Sin actividad motora"
        )

        # Mech metrics
        mech_vars["height"].set(f"{float(payload['height']):+.3f} m")
        mech_vars["motion"].set(f"{float(payload['joint_motion']):.2f} rad/s")
        mech_vars["work"].set(f"{float(payload['mechanical_work_joules']):.4f} J")
        mech_vars["cost"].set(f"{float(payload['metabolic_work_cost']):.5f}")

        # HUD Top
        origin = str(payload.get("motor_origin", "none"))
        badge_color = motor_origin_colors.get(origin, "#374151")
        motor_origin_badge.configure(text=f"ORIGEN: {origin.upper()}", bg=badge_color)

        dist = float(payload.get("resource_distance", 0.0))
        prog = float(payload.get("resource_progress", 0.0))
        sign = "+" if prog >= 0 else ""
        resource_hud_badge.configure(text=f"RECURSO: {dist:.2f}m · PROGRESO NETO: {sign}{prog:.2f}m")

        # Situational overview. These labels are deterministic summaries of
        # evaluator metrics; clicking them opens the underlying technical data.
        motion = float(payload["joint_motion"])
        behavior_detail_vars["activity"].set(f"ACTIVIDAD · {motion:.2f} rad/s")
        if motion < 0.05:
            movement_state = "QUIETO"
        elif motion < 0.50:
            movement_state = "SUAVE"
        elif motion < 2.00:
            movement_state = "MODERADO"
        else:
            movement_state = "ALTO"
        situation_vars["behavior"].set(f"MOVIMIENTO · {movement_state} · {motion:.2f} rad/s")

        primitive_active = bool(payload.get("primitive_replay_active", False))
        cognitive_primitives = int(payload.get("cognitive_motor_primitives", 0))
        sensorimotor_patterns = int(payload.get("sensorimotor_patterns", 0))
        if primitive_active:
            learning_state = "REUTILIZA PRIMITIVA"
        elif origin == "cognition" and cognitive_primitives > 0:
            learning_state = "APLICANDO"
        elif int(payload.get("predictor_count", 0)) > 0 or sensorimotor_patterns > 0:
            learning_state = "APRENDIENDO"
        else:
            learning_state = "OBSERVANDO"
        situation_vars["learning"].set(f"APRENDIZAJE · {learning_state}")

        motor_control = max(
            0.0,
            min(
                1.0,
                (
                    max(0.0, float(payload.get("best_motor_controllability", 0.0)))
                    * max(0.0, float(payload.get("best_motor_directional_consistency", 0.0)))
                )
                ** 0.5,
            ),
        )
        behavior_detail_vars["control"].set(f"CONTROL MOTOR · {motor_control:.2f}")

        if len(trajectory_history) >= 2:
            first = trajectory_history[max(0, len(trajectory_history) - 12)]
            last = trajectory_history[-1]
            locomotion_delta = (
                (last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2
            ) ** 0.5
        else:
            locomotion_delta = 0.0
        behavior_detail_vars["locomotion"].set(
            f"LOCOMOCIÓN · Δ {locomotion_delta:.3f} m"
        )

        reserve_now = float(payload["metabolic_reserve_ratio"])
        reserve_trend_source = reserve_history
        previous_reserve = (
            reserve_trend_source[-min(12, len(reserve_trend_source))]
            if reserve_trend_source
            else reserve_now
        )
        reserve_delta = reserve_now - previous_reserve
        energy_arrow = "↑" if reserve_delta > 0.002 else ("↓" if reserve_delta < -0.002 else "↔")
        situation_vars["energy"].set(f"ENERGÍA · {reserve_now * 100.0:.0f}% {energy_arrow}")

        distance_trend_source = resource_raw_history
        previous_dist = (
            distance_trend_source[-min(12, len(distance_trend_source))]
            if distance_trend_source
            else dist
        )
        distance_delta = dist - previous_dist
        if distance_delta < -0.005:
            resource_state = "SE ACERCA ↓"
        elif distance_delta > 0.005:
            resource_state = "SE ALEJA ↑"
        else:
            resource_state = "SIN CAMBIO ↔"
        situation_vars["goal"].set(f"RECURSO · {resource_state} · {dist:.2f} m")

        # Card 1: Cognition
        conf = float(payload["schema_confidence"])
        cog_vars["schema"].set(f"{conf * 100.0:.1f}%")
        try:
            schema_bar_canvas.coords(schema_bar_rect, 0, 0, int(conf * 280), 8)
        except Exception:
            schema_bar_canvas.delete("all")
            schema_bar_canvas.create_rectangle(0, 0, int(conf * 280), 8, fill=green, width=0)

        parts = int(payload["schema_parts"])
        senses = int(payload["schema_sensory_parts"])
        cog_vars["parts"].set(f"{parts} partes ({senses} sensores)")

        regions = int(payload["schema_cognitive_regions"])
        evid = int(payload["schema_dependency_evidence"])
        cog_vars["regions"].set(f"{regions} regiones ({evid} evidencias)")

        pred_count = int(payload["predictor_count"])
        p_err = payload.get("prediction_error")
        err_str = "N/A" if p_err is None else f"{float(p_err):.3f}"
        cog_vars["predictors"].set(f"{pred_count} act. (error: {err_str})")

        shadows = int(payload["shadow_prediction_count"])
        prom = int(payload["promotable_shadow_count"])
        cog_vars["shadows"].set(f"{shadows} sombras ({prom} prom.)")
        cog_vars["error"].set(err_str)

        # Card 2: Ecology & Metabolism
        reserve = float(payload["metabolic_reserve_ratio"])
        absorbed = float(payload["absorbed_energy"])
        eco_vars["reserve"].set(f"{reserve * 100.0:.1f}% (+{absorbed:.3f})")
        res_color = green if reserve > 0.5 else (yellow if reserve > 0.25 else red)
        try:
            reserve_bar_canvas.coords(reserve_bar_rect, 0, 0, int(reserve * 280), 8)
            reserve_bar_canvas.itemconfigure(reserve_bar_rect, fill=res_color)
        except Exception:
            reserve_bar_canvas.delete("all")
            reserve_bar_canvas.create_rectangle(0, 0, int(reserve * 280), 8, fill=res_color, width=0)

        d_min = float(payload["minimum_resource_distance"])
        eco_vars["distance"].set(f"{dist:.3f} m (mín: {d_min:.3f}m)")
        eco_vars["progress"].set(f"{sign}{prog:.3f} m")
        eco_vars["displacement"].set(f"{float(payload['displacement_from_origin']):.3f} m")

        rep_size = int(payload["motor_repertoire_size"])
        cov = float(payload["sensorimotor_coverage"]) * 100.0
        eco_vars["repertoire"].set(f"{rep_size} pat. (cobertura {cov:.1f}%)")

        m_prim = int(payload["motor_primitives"])
        c_prim = int(payload["cognitive_motor_primitives"])
        eco_vars["primitives"].set(f"{m_prim} prim. ({c_prim} cognitivas)")

        ctrl = float(payload["best_motor_controllability"])
        cons = float(payload["best_motor_directional_consistency"])
        eco_vars["control"].set(f"ctrl {ctrl:.2f} · dir {cons:.2f}")

        eco_vars["origins"].set(
            f"C:{int(payload['motor_origin_cognition'])} "
            f"B:{int(payload.get('motor_origin_babbling', 0))} "
            f"P:{int(payload.get('motor_origin_primitive', 0))} "
            f"M:{int(payload.get('motor_origin_mixed', 0))} "
            f"S:{int(payload['motor_origin_spontaneous'])}"
        )

        # Card 3: Private SLM
        slm_recs = int(payload["slm_records"])
        slm_trans = int(payload["slm_transition_records"])
        slm_vars["records"].set(f"{slm_recs:,} exp. ({slm_trans:,} trans.)")

        is_act = payload["slm_active"]
        is_trn = payload["slm_training"]
        st_text = "ACTIVO" if is_act else ("ENTRENANDO" if is_trn else "SHADOW")
        models = int(payload["slm_models"])
        slm_vars["state"].set(f"{st_text} ({models} mod.)")

        gain = payload.get("slm_gate_gain")
        gain_str = "—" if gain is None else f"{float(gain):+.3f}"
        gate = str(payload.get("slm_gate_reason") or "—")
        slm_vars["gate"].set(f"{gate} (ganancia: {gain_str})")

        cand_loss = payload.get("slm_candidate_loss")
        base_loss = payload.get("slm_best_baseline_loss")
        if cand_loss is not None and base_loss is not None:
            slm_vars["loss"].set(f"{float(cand_loss):.3f} vs {float(base_loss):.3f}")
        else:
            slm_vars["loss"].set("—")

        # Bottom timing & checkpoint
        cycle_t = float(payload["cycle_ms"])
        org_t = float(payload["organism_ms"])
        phy_t = float(payload["physics_ms"])
        chk_age = int(payload["checkpoint_age"])
        timing_var.set(f"Ciclo: {cycle_t:.1f}ms (Org {org_t:.1f}ms · Fis {phy_t:.1f}ms) · Checkpoint hace {chk_age:,} ticks")

        if panel_visibility["timeline"]:
            draw_chart()

    last_render_time = 0.0
    MIN_RENDER_INTERVAL = 0.030  # Cap 3D scene rendering to ~33 FPS max

    def apply_frame(message: dict, render: bool = True) -> None:
        nonlocal latest_physical_state, previous_event_snapshot, last_render_time
        state = message.get("physical_state")
        if not isinstance(state, dict):
            return
        latest_physical_state = state
        current_snapshot = message.get("snapshot")
        if isinstance(current_snapshot, dict):
            record_events(previous_event_snapshot, current_snapshot)
            previous_event_snapshot = dict(current_snapshot)
            snapshot_history.append(dict(current_snapshot))
            del snapshot_history[:-max_history]
        pos = state.get("base_position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 3:
            trajectory_history.append((float(pos[0]), float(pos[1]), float(pos[2])))
            del trajectory_history[:-max_trajectory]
        now = time.monotonic()
        render_error = None
        if render and (now - last_render_time >= MIN_RENDER_INTERVAL):
            try:
                render_scene(state)
                last_render_time = now
            except Exception as exc:
                render_error = f"{type(exc).__name__}: {exc}"
        apply_snapshot(message["snapshot"], state, update_ui=render)
        if render_error is not None:
            scene_label.configure(
                image="",
                text=f"Error render 3D\n{render_error}",
                fg=red,
                bg="#090d11",
                font=("TkFixedFont", 10),
            )

    def request_stop() -> None:
        if command_queue is not None:
            _put_latest(command_queue, {"type": "stop"})
        try:
            p.disconnect(physicsClientId=render_client)
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", request_stop)

    def poll() -> None:
        if frame_queue is None:
            return
        frames = []
        should_close = False
        while True:
            try:
                message = frame_queue.get_nowait()
            except queue.Empty:
                break
            if message.get("type") == "close":
                should_close = True
                break
            if message.get("type") == "frame":
                frames.append(message)
        if should_close:
            try:
                p.disconnect(physicsClientId=render_client)
            except Exception:
                pass
            root.destroy()
            return
        if frames:
            for f in frames[:-1]:
                apply_frame(f, render=False)
            apply_frame(frames[-1], render=True)
        root.after(30, poll)

    if not is_replay:
        root.after(40, poll)
    else:
        root.after(50, lambda: load_replay_tick(0))
    root.mainloop()


__all__ = [
    "CameraState",
    "MonitorProcess",
    "MonitorSnapshot",
    "PillFrame",
    "UnifiedViewerProcess",
    "_viewer_main",
    "record_to_snapshot",
    "snapshot_to_physical_state",
    "strongest_outputs",
    "_event_transition",
    "_event_context",
]
