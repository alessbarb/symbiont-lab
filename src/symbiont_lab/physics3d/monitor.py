"""Unified passive Physics3D viewer.

PyBullet remains in the parent process as the physical apparatus. This module
runs one Tkinter window in a separate process and receives bounded evaluator
snapshots plus RGB camera frames. It can only send camera/viewer lifecycle
commands back to the parent; there is no control path into cognition.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from multiprocessing.context import BaseContext
import os
import queue
import signal
from typing import Mapping


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
    joints = record.get("joints")
    if not joints or not isinstance(joints, (list, tuple)):
        joints = [
            {
                "joint_index": j_id,
                "position": 0.0,
                "velocity": 0.0,
                "applied_torque": 0.0,
            }
            for j_id in range(2, 10)
        ]
    contact_links = record.get("contact_links", ())
    base_pos = record.get("base_position", (0.0, 0.0, 0.9))
    base_orient = record.get("base_orientation", (0.0, 0.0, 0.0, 1.0))
    res_info = record.get("locomotion_resource")
    if isinstance(res_info, dict):
        res_pos = res_info.get("position", (float(base_pos[0]) + 3.0, float(base_pos[1]), 0.15))
        res_rem = float(res_info.get("remaining", 200.0))
    else:
        res_dist = float(record.get("resource_distance", 3.0))
        res_rem = float(record.get("resource_remaining", 200.0))
        res_pos = (float(base_pos[0]) + res_dist, float(base_pos[1]), 0.15)
    return {
        "schema_version": 1,
        "body_kind": "anthropomorphic-v0",
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
        from PIL import Image, ImageTk
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
        f = tk.Frame(parent, bg=bg_color, padx=8, pady=3, highlightthickness=1, highlightbackground=border)
        f.pack(side="left", padx=4)
        l = tk.Label(f, textvariable=text_var, bg=bg_color, fg=fg_color, font=("TkDefaultFont", 8, "bold"))
        l.pack()
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

    sim_state_pill_var = tk.StringVar(value="PAUSADO" if is_replay else "EJECUTANDO")
    sim_pill_frame = make_pill(header_status_box, sim_state_pill_var, cyan, "#1e293b")

    # -------------------------------------------------------------
    # 2. MAIN WORKSPACE (Row 1: Left - Center - Right)
    # -------------------------------------------------------------
    workspace = tk.Frame(root, bg=bg)
    workspace.grid(row=1, column=0, sticky="nsew")
    workspace.grid_rowconfigure(0, weight=1)
    workspace.grid_columnconfigure(0, minsize=290, weight=0)
    workspace.grid_columnconfigure(1, weight=1)
    workspace.grid_columnconfigure(2, minsize=350, weight=0)

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
        (3, "Mano Izq.", 1, 0, 1),
        (5, "Mano Der.", 1, 1, 1),
        (7, "Pie Izq.", 2, 0, 1),
        (9, "Pie Der.", 2, 1, 1),
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
        2: "Hombro Izq.",
        3: "Codo Izq.",
        4: "Hombro Der.",
        5: "Codo Der.",
        6: "Cadera Izq.",
        7: "Rodilla Izq.",
        8: "Cadera Der.",
        9: "Rodilla Der.",
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
        joint_canvases[j_id] = cv
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
    center_panel.grid_rowconfigure(1, weight=1)
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

    # 3D Scene Label
    scene_panel = tk.Frame(center_panel, bg="#090d11")
    scene_panel.grid(row=1, column=0, sticky="nsew")
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

    # Bottom Camera & Controls HUD
    hud_bottom = tk.Frame(center_panel, bg="#090d11", padx=8, pady=6)
    hud_bottom.grid(row=2, column=0, sticky="ew")

    camera_btn_frame = tk.Frame(hud_bottom, bg="#090d11")
    camera_btn_frame.pack(side="left")

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
    make_cam_btn("🔍 Zoom", CameraState(38.0, -15.0, 1.8, 0.85))

    tk.Label(
        hud_bottom,
        text="Arrastra: Orbitar · Rueda: Zoom · Tecla Espacio: Pausa",
        bg="#090d11",
        fg=muted,
        font=("TkDefaultFont", 7),
    ).pack(side="right")

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

    # -------------------------------------------------------------
    # 3. BOTTOM PANEL: TELEMETRY TIME-SERIES & CONTROLS (Row 2)
    # -------------------------------------------------------------
    bottom_frame = tk.Frame(root, bg=panel, padx=12, pady=6, highlightthickness=1, highlightbackground=border)
    bottom_frame.grid(row=2, column=0, sticky="ew")
    bottom_frame.grid_columnconfigure(0, weight=1)
    bottom_frame.grid_columnconfigure(1, minsize=320, weight=0)

    chart_box = tk.Frame(bottom_frame, bg=panel)
    chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    chart = tk.Canvas(chart_box, height=130, bg="#090d11", highlightthickness=1, highlightbackground=border)
    chart.pack(fill="both", expand=True)

    ctrl_box = tk.Frame(bottom_frame, bg=sub_bg, padx=10, pady=8, highlightthickness=1, highlightbackground=border)
    ctrl_box.grid(row=0, column=1, sticky="nsew")

    if is_replay:
        tk.Label(ctrl_box, text="CONTROL DE REPLAY", bg=sub_bg, fg=cyan, font=("TkDefaultFont", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 2))

        slider_var = tk.DoubleVar(value=0)
        is_scrubbing = False
        current_replay_idx = 0
        is_playing = False
        replay_speed = 1.0

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
            for r in replay_records[window_start : current_replay_idx + 1]:
                err = r.get("prediction_error")
                if err is not None:
                    prediction_history.append(float(err))
                schema_history.append(float(r.get("schema_confidence", 0.0)))
                d = float(r.get("resource_distance", 0.0))
                resource_dist_history.append(max(0.0, min(1.0, d / 5.0)))

            p_state = snapshot_to_physical_state(rec)
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
        root.bind("r", lambda _e: make_cam_btn("", CameraState(38.0, -20.0, 3.1, 0.85)).invoke())
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

        timing_var = tk.StringVar(value="Ciclo: — · Checkpoint: —")
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
        root.bind("r", lambda _e: make_cam_btn("", CameraState(38.0, -20.0, 3.1, 0.85)).invoke())

    # -------------------------------------------------------------
    # 3D CAMERA & SCENE RENDER LOGIC
    # -------------------------------------------------------------
    camera = CameraState()
    drag_origin: tuple[int, int, float, float] | None = None
    latest_physical_state: dict[str, object] | None = None
    render_pending = False
    photo_ref = None

    def render_scene(physical_state: dict[str, object]) -> None:
        nonlocal photo_ref
        render_body.restore_physical_state(physical_state)
        resource_state = physical_state.get("locomotion_resource")
        if isinstance(resource_state, dict):
            position = resource_state.get("position")
            if isinstance(position, (list, tuple)) and len(position) == 3:
                p.resetBasePositionAndOrientation(
                    render_resource.body_id,
                    tuple(float(value) for value in position),
                    (0.0, 0.0, 0.0, 1.0),
                    physicsClientId=render_client,
                )
            remaining = float(resource_state.get("remaining", 0.0))
            alpha = 1.0 if remaining > 0.0 else 0.15
            p.changeVisualShape(
                render_resource.body_id,
                -1,
                rgbaColor=(0.52, 0.78, 0.36, alpha),
                physicsClientId=render_client,
            )
        width, height = 720, 480
        base_position, _ = p.getBasePositionAndOrientation(
            render_body.body_id,
            physicsClientId=render_client,
        )
        target = (
            float(base_position[0]),
            float(base_position[1]),
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
        image_data = p.getCameraImage(
            width=width,
            height=height,
            viewMatrix=view,
            projectionMatrix=projection,
            renderer=p.ER_TINY_RENDERER,
            flags=p.ER_NO_SEGMENTATION_MASK,
            physicsClientId=render_client,
        )
        rgba = np.asarray(image_data[2], dtype=np.uint8).reshape(height, width, 4)
        image = Image.fromarray(rgba[:, :, :3], mode="RGB")
        label_w = max(1, scene_label.winfo_width())
        label_h = max(1, scene_label.winfo_height())
        scale = min(label_w / width, label_h / height)
        if scale > 0 and abs(scale - 1.0) > 0.04:
            target_size = (
                max(1, int(width * scale)),
                max(1, int(height * scale)),
            )
            image = image.resize(target_size, Image.Resampling.BILINEAR)
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
    scene_label.bind("<MouseWheel>", on_wheel)
    scene_label.bind("<Button-4>", on_wheel)
    scene_label.bind("<Button-5>", on_wheel)

    # -------------------------------------------------------------
    # TELEMETRY SERIES & MULTI-PARAM CHART
    # -------------------------------------------------------------
    prediction_history: list[float] = []
    schema_history: list[float] = []
    resource_dist_history: list[float] = []
    max_history = 180

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
        chart.create_text(pad_l + 484, 12, text="Distancia Recurso (Norm.)", fill=cyan, anchor="w", font=("TkDefaultFont", 7))

        # Grid lines
        for step in (0.25, 0.50, 0.75, 1.00):
            y_grid = pad_t + graph_h * (1.0 - step)
            chart.create_line(pad_l, y_grid, pad_l + graph_w, y_grid, fill="#1c232d", dash=(2, 4))
        chart.create_line(pad_l, pad_t, pad_l, pad_t + graph_h, fill=border)
        chart.create_line(pad_l, pad_t + graph_h, pad_l + graph_w, pad_t + graph_h, fill=border)

        def series(values: list[float], color: str) -> None:
            if len(values) < 2:
                return
            points = []
            for index, value in enumerate(values):
                x = pad_l + graph_w * index / max(1, len(values) - 1)
                bounded = max(0.0, min(1.0, float(value)))
                y = pad_t + graph_h * (1.0 - bounded)
                points.extend((x, y))
            chart.create_line(*points, fill=color, width=2)

        series(prediction_history, orange)
        series(schema_history, green)
        series(resource_dist_history, cyan)

    # -------------------------------------------------------------
    # SNAPSHOT UPDATE LOGIC
    # -------------------------------------------------------------
    motor_origin_colors = {
        "cognition": "#1d4ed8",
        "babbling": "#0891b2",
        "primitive": "#059669",
        "mixed": "#7c3aed",
        "spontaneous": "#d97706",
        "probe": "#0f766e",
        "none": "#374151",
    }

    def apply_snapshot(payload: dict, physical_state: dict) -> None:
        # Header
        identity_var.set(f"{payload['symbiont_id']}")
        tick_pill_var.set(f"TICK: {int(payload['tick']):,}")
        realtime_pill_var.set(f"{float(payload['realtime_ratio']):.2f}x")

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
                cv = joint_canvases[j_id]
                cv.delete("all")
                # draw center reference notch
                cv.create_line(60, 0, 60, 13, fill="#30363d")
                ratio = max(-1.0, min(1.0, torque / max_t))
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

        # Card 1: Cognition
        conf = float(payload["schema_confidence"])
        cog_vars["schema"].set(f"{conf * 100.0:.1f}%")
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
        reserve_bar_canvas.delete("all")
        res_color = green if reserve > 0.5 else (yellow if reserve > 0.25 else red)
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

        # Update History & Chart
        if p_err is not None:
            prediction_history.append(float(p_err))
        schema_history.append(conf)
        # normalize resource distance (assuming 0-5m range)
        resource_dist_history.append(max(0.0, min(1.0, dist / 5.0)))

        del prediction_history[:-max_history]
        del schema_history[:-max_history]
        del resource_dist_history[:-max_history]
        draw_chart()

    def apply_frame(message: dict) -> None:
        nonlocal latest_physical_state
        state = message.get("physical_state")
        if not isinstance(state, dict):
            return
        latest_physical_state = state
        render_scene(state)
        apply_snapshot(message["snapshot"], state)

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
        latest = None
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
                latest = message
        if should_close:
            try:
                p.disconnect(physicsClientId=render_client)
            except Exception:
                pass
            root.destroy()
            return
        if latest is not None:
            apply_frame(latest)
        root.after(40, poll)

    if not is_replay:
        root.after(40, poll)
    else:
        root.after(50, lambda: load_replay_tick(0))
    root.mainloop()


__all__ = [
    "CameraState",
    "MonitorProcess",
    "MonitorSnapshot",
    "UnifiedViewerProcess",
    "_viewer_main",
    "record_to_snapshot",
    "snapshot_to_physical_state",
    "strongest_outputs",
]
