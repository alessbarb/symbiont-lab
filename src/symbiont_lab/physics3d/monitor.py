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
        self._commands = context.Queue(maxsize=4)
        self._process = context.Process(
            target=_viewer_main,
            args=(self._frames, self._commands),
            daemon=True,
            name="symbiont-3d-viewer",
        )

    def start(self) -> None:
        self._process.start()

    @property
    def is_alive(self) -> bool:
        return self._process.is_alive()

    def poll_stop(self) -> bool:
        stop = not self._process.is_alive()
        while True:
            try:
                message = self._commands.get_nowait()
            except queue.Empty:
                break
            if message.get("type") == "stop":
                stop = True
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


def _viewer_main(frame_queue, command_queue) -> None:
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

    bg = "#11161c"
    panel = "#18212b"
    fg = "#e8eef5"
    muted = "#93a4b8"
    cyan = "#73d7d2"
    orange = "#ee936f"
    green = "#79d894"

    root = tk.Tk()
    root.title("Symbiont 3D")
    root.geometry("1420x860")
    root.minsize(1080, 680)
    root.configure(bg=bg)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=panel,
        foreground=fg,
        padding=(10, 7),
    )
    style.map("TNotebook.Tab", background=[("selected", "#243341")])

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

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, minsize=405)

    scene_panel = tk.Frame(root, bg="#090d11")
    scene_panel.grid(row=0, column=0, sticky="nsew")
    scene_panel.grid_rowconfigure(0, weight=1)
    scene_panel.grid_columnconfigure(0, weight=1)

    scene_label = tk.Label(
        scene_panel,
        bg="#090d11",
        fg=muted,
        text="waiting for first 3D frame…",
        anchor="center",
    )
    scene_label.grid(row=0, column=0, sticky="nsew")

    camera_help = tk.Label(
        scene_panel,
        text="Arrastra para orbitar · rueda para zoom",
        bg="#090d11",
        fg=muted,
        font=("TkDefaultFont", 8),
        padx=10,
        pady=6,
    )
    camera_help.grid(row=1, column=0, sticky="ew")

    sidebar = tk.Frame(root, bg=bg, width=405)
    sidebar.grid(row=0, column=1, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.grid_rowconfigure(2, weight=1)
    sidebar.grid_columnconfigure(0, weight=1)

    identity_var = tk.StringVar(value="waiting for physics…")
    tk.Label(
        sidebar,
        text="SYMBIONT 3D",
        bg=bg,
        fg=fg,
        font=("TkDefaultFont", 15, "bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 2))
    tk.Label(
        sidebar,
        textvariable=identity_var,
        bg=bg,
        fg=muted,
        font=("TkDefaultFont", 8),
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

    notebook = ttk.Notebook(sidebar)
    notebook.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))

    runtime_tab = tk.Frame(notebook, bg=bg)
    cognition_tab = tk.Frame(notebook, bg=bg)
    slm_tab = tk.Frame(notebook, bg=bg)
    ecology_tab = tk.Frame(notebook, bg=bg)
    notebook.add(runtime_tab, text="Runtime")
    notebook.add(cognition_tab, text="Body & Cognition")
    notebook.add(slm_tab, text="Private SLM")
    notebook.add(ecology_tab, text="Ecology")

    def make_metrics(parent, specs):
        frame = tk.Frame(parent, bg=panel, padx=10, pady=9)
        frame.pack(fill="x", padx=6, pady=6)
        values = {}
        for row, (key, label) in enumerate(specs):
            tk.Label(
                frame,
                text=label,
                bg=panel,
                fg=muted,
                font=("TkDefaultFont", 8),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=2)
            value = tk.StringVar(value="—")
            values[key] = value
            tk.Label(
                frame,
                textvariable=value,
                bg=panel,
                fg=fg,
                font=("TkDefaultFont", 9, "bold"),
                anchor="e",
            ).grid(row=row, column=1, sticky="e", padx=(16, 0), pady=2)
        frame.grid_columnconfigure(1, weight=1)
        return values

    runtime_vars = make_metrics(runtime_tab, (
        ("tick", "Tick"),
        ("mode", "Embodiment"),
        ("outputs", "Active outputs"),
        ("motion", "Joint motion"),
        ("contacts", "Contacts"),
        ("work", "Mechanical work"),
        ("work_cost", "Metabolic work cost"),
        ("height", "Body height"),
        ("checkpoint", "Checkpoint age"),
        ("cycle_ms", "Cognitive cycle"),
        ("organism_ms", "  organism"),
        ("physics_ms", "  physics"),
        ("diagnostics_ms", "  diagnostics"),
        ("realtime", "Realtime"),
    ))

    outputs_var = tk.StringVar(value="No motor activity yet")
    tk.Label(
        runtime_tab,
        text="OPAQUE MOTOR ACTIVITY",
        bg=bg,
        fg=cyan,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=8, pady=(5, 2))
    tk.Label(
        runtime_tab,
        textvariable=outputs_var,
        bg=panel,
        fg=fg,
        font=("TkFixedFont", 9),
        justify="left",
        anchor="nw",
        padx=8,
        pady=8,
    ).pack(fill="x", padx=6, pady=(0, 6))

    cognition_vars = make_metrics(cognition_tab, (
        ("schema", "BodySchema confidence"),
        ("schema_parts", "Parts"),
        ("schema_senses", "  sensory parts"),
        ("schema_regions", "  cognitive regions"),
        ("schema_evidence", "  dependency evidence"),
        ("schema_deps", "  exported dependencies"),
        ("predictors", "Predictors"),
        ("shadow_predictions", "Shadow predictions"),
        ("promotable_shadows", "  promotable"),
        ("error", "Prediction error"),
    ))

    chart = tk.Canvas(
        cognition_tab,
        height=235,
        bg=panel,
        highlightthickness=0,
    )
    chart.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    slm_vars = make_metrics(slm_tab, (
        ("slm_records", "Experiences"),
        ("slm_transitions", "Temporal transitions"),
        ("slm_models", "Models"),
        ("slm_active", "Active"),
        ("slm_training", "Training"),
        ("slm_error", "Status"),
        ("slm_gate", "Last gate"),
        ("slm_gain", "Gain vs baseline"),
        ("slm_baseline", "Best baseline / model"),
    ))

    ecology_vars = make_metrics(ecology_tab, (
        ("distance", "Resource distance"),
        ("field", "Opaque field"),
        ("reserve", "Metabolic reserve"),
        ("absorbed", "Absorbed this tick"),
        ("remaining", "Resource remaining"),
        ("displacement", "Displacement from birth"),
        ("motor_origin", "Motor origin"),
    ))

    file_var = tk.StringVar(value="")
    tk.Label(
        slm_tab,
        text="PORTABLE SYMBIONT",
        bg=bg,
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=8, pady=(8, 2))
    tk.Label(
        slm_tab,
        textvariable=file_var,
        bg=bg,
        fg=muted,
        font=("TkDefaultFont", 8),
        justify="left",
        wraplength=365,
        anchor="w",
    ).pack(fill="x", padx=8, pady=(0, 8))

    camera = CameraState()
    drag_origin: tuple[int, int, float, float] | None = None

    latest_physical_state: dict[str, object] | None = None
    render_pending = False

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

    prediction_history: list[float] = []
    schema_history: list[float] = []
    max_history = 120
    photo_ref = None

    def draw_chart() -> None:
        chart.delete("all")
        width = max(1, chart.winfo_width())
        height = max(1, chart.winfo_height())
        pad = 28
        graph_w = max(1, width - pad * 2)
        graph_h = max(1, height - 54)
        chart.create_text(
            pad, 12, text="rolling learning signals", fill=muted,
            anchor="w", font=("TkDefaultFont", 8),
        )
        chart.create_line(pad, 30, pad, 30 + graph_h, fill="#354252")
        chart.create_line(pad, 30 + graph_h, pad + graph_w, 30 + graph_h, fill="#354252")

        def series(values: list[float], color: str) -> None:
            if len(values) < 2:
                return
            points = []
            for index, value in enumerate(values):
                x = pad + graph_w * index / max(1, len(values) - 1)
                bounded = max(0.0, min(1.0, float(value)))
                y = 30 + graph_h * (1.0 - bounded)
                points.extend((x, y))
            chart.create_line(*points, fill=color, width=2)

        series(prediction_history, orange)
        series(schema_history, green)
        chart.create_text(
            pad, height - 10,
            text="prediction error", fill=orange,
            anchor="w", font=("TkDefaultFont", 8),
        )
        chart.create_text(
            pad + 150, height - 10,
            text="body schema", fill=green,
            anchor="w", font=("TkDefaultFont", 8),
        )

    def apply_snapshot(payload: dict) -> None:
        identity_var.set(f"{payload['symbiont_id']} · passive evaluator")
        runtime_vars["tick"].set(f"{int(payload['tick']):,}")
        runtime_vars["mode"].set(str(payload["embodiment_mode"]))
        runtime_vars["outputs"].set(str(int(payload["active_effectors"])))
        runtime_vars["motion"].set(f"{float(payload['joint_motion']):.2f}")
        runtime_vars["contacts"].set(str(int(payload["contact_count"])))
        runtime_vars["work"].set(f"{float(payload['mechanical_work_joules']):.4f} J")
        runtime_vars["work_cost"].set(f"{float(payload['metabolic_work_cost']):.5f}")
        runtime_vars["height"].set(f"{float(payload['height']):+.3f} m")
        runtime_vars["checkpoint"].set(f"{int(payload['checkpoint_age']):,} ticks")
        runtime_vars["cycle_ms"].set(f"{float(payload['cycle_ms']):.1f} ms")
        runtime_vars["organism_ms"].set(f"{float(payload['organism_ms']):.1f} ms")
        runtime_vars["physics_ms"].set(f"{float(payload['physics_ms']):.1f} ms")
        runtime_vars["diagnostics_ms"].set(f"{float(payload['diagnostics_ms']):.1f} ms")
        runtime_vars["realtime"].set(f"{float(payload['realtime_ratio']):.2f}x")

        ecology_vars["distance"].set(f"{float(payload['resource_distance']):.3f} m")
        ecology_vars["field"].set(f"{float(payload['resource_field']):.4f}")
        ecology_vars["reserve"].set(f"{100.0 * float(payload['metabolic_reserve_ratio']):.1f}%")
        ecology_vars["absorbed"].set(f"{float(payload['absorbed_energy']):.4f}")
        ecology_vars["remaining"].set(f"{float(payload['resource_remaining']):.2f}")
        ecology_vars["displacement"].set(f"{float(payload['displacement_from_origin']):.3f} m")
        ecology_vars["motor_origin"].set(str(payload["motor_origin"]))

        strongest = payload.get("strongest_outputs", ())
        outputs_var.set(
            "\n".join(
                f"{str(channel):<9} {float(value):.3f}"
                for channel, value in strongest
            ) or "No motor activity yet"
        )

        cognition_vars["schema"].set(f"{float(payload['schema_confidence']):.3f}")
        cognition_vars["schema_parts"].set(str(int(payload["schema_parts"])))
        cognition_vars["schema_senses"].set(str(int(payload["schema_sensory_parts"])))
        cognition_vars["schema_regions"].set(str(int(payload["schema_cognitive_regions"])))
        cognition_vars["schema_evidence"].set(str(int(payload["schema_dependency_evidence"])))
        cognition_vars["schema_deps"].set(str(int(payload["schema_dependencies"])))
        cognition_vars["predictors"].set(str(int(payload["predictor_count"])))
        cognition_vars["shadow_predictions"].set(
            str(int(payload["shadow_prediction_count"]))
        )
        cognition_vars["promotable_shadows"].set(
            str(int(payload["promotable_shadow_count"]))
        )
        prediction_error = payload.get("prediction_error")
        cognition_vars["error"].set(
            "N/A" if prediction_error is None else f"{float(prediction_error):.3f}"
        )

        slm_vars["slm_records"].set(f"{int(payload['slm_records']):,}")
        slm_vars["slm_transitions"].set(f"{int(payload['slm_transition_records']):,}")
        slm_vars["slm_models"].set(str(int(payload["slm_models"])))
        slm_vars["slm_active"].set("yes" if payload["slm_active"] else "no")
        slm_vars["slm_training"].set("yes" if payload["slm_training"] else "no")
        slm_vars["slm_error"].set(str(payload["slm_error"] or "ok"))
        slm_vars["slm_gate"].set(str(payload.get("slm_gate_reason") or "—"))
        gain = payload.get("slm_gate_gain")
        slm_vars["slm_gain"].set("—" if gain is None else f"{float(gain):+.3f}")
        baseline = payload.get("slm_best_baseline")
        candidate_loss = payload.get("slm_candidate_loss")
        baseline_loss = payload.get("slm_best_baseline_loss")
        if baseline is None or candidate_loss is None or baseline_loss is None:
            slm_vars["slm_baseline"].set("—")
        else:
            slm_vars["slm_baseline"].set(
                f"{baseline} {float(baseline_loss):.3f} / "
                f"model {float(candidate_loss):.3f}"
            )
        file_var.set(str(payload["symbiont_file"]))

        if prediction_error is not None:
            prediction_history.append(float(prediction_error))
        schema_history.append(float(payload["schema_confidence"]))
        del prediction_history[:-max_history]
        del schema_history[:-max_history]
        draw_chart()

    def apply_frame(message: dict) -> None:
        nonlocal latest_physical_state
        state = message.get("physical_state")
        if not isinstance(state, dict):
            return
        latest_physical_state = state
        render_scene(state)
        apply_snapshot(message["snapshot"])

    def request_stop() -> None:
        _put_latest(command_queue, {"type": "stop"})
        try:
            p.disconnect(physicsClientId=render_client)
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", request_stop)

    def poll() -> None:
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
        root.after(50, poll)

    root.after(50, poll)
    root.mainloop()


__all__ = [
    "CameraState",
    "MonitorProcess",
    "MonitorSnapshot",
    "UnifiedViewerProcess",
    "strongest_outputs",
]
