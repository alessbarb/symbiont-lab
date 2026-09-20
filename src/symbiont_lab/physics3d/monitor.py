"""Separate lightweight monitor windows for Physics3D.

The monitor runs in its own process and receives evaluator-only snapshots through
a bounded multiprocessing queue. It never imports PyBullet and has no path back
into cognition or physics.

The evaluator is split into several always-on-top windows so the 3D scene remains
visible and interactive while diagnostics stay legible. "Modal" here means
visually attached/topmost, never input-blocking: a blocking GUI modal would halt
or interfere with observation of the running experiment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from multiprocessing.context import BaseContext
import queue
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
    """Keep producer non-blocking by dropping stale monitor frames."""
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


class MonitorProcess:
    """Small lifecycle wrapper around the external Tkinter evaluator."""

    def __init__(self, context: BaseContext) -> None:
        self._queue = context.Queue(maxsize=2)
        self._process = context.Process(
            target=_monitor_main,
            args=(self._queue,),
            daemon=True,
            name="symbiont-3d-monitor",
        )

    def start(self) -> None:
        self._process.start()

    def publish(self, snapshot: MonitorSnapshot) -> None:
        if not self._process.is_alive():
            return
        _put_latest(self._queue, {"type": "snapshot", "payload": asdict(snapshot)})

    def close(self) -> None:
        if self._process.is_alive():
            _put_latest(self._queue, {"type": "close"})
            self._process.join(timeout=1.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)


def _monitor_main(source_queue) -> None:
    try:
        import tkinter as tk
    except ImportError:
        print("Physics3D monitor unavailable: tkinter is not installed.")
        return

    bg = "#11161c"
    panel = "#18212b"
    fg = "#e8eef5"
    muted = "#93a4b8"
    cyan = "#73d7d2"
    orange = "#ee936f"
    green = "#79d894"

    root = tk.Tk()
    root.title("Symbiont 3D — Runtime")
    root.geometry("370x410+20+70")
    root.minsize(340, 370)
    root.configure(bg=bg)

    cognition = tk.Toplevel(root)
    cognition.title("Symbiont 3D — Body & Cognition")
    cognition.geometry("430x505+20+445")
    cognition.minsize(390, 430)
    cognition.configure(bg=bg)

    slm = tk.Toplevel(root)
    slm.title("Symbiont 3D — Private SLM")
    slm.geometry("430x430+390+70")
    slm.minsize(390, 370)
    slm.configure(bg=bg)

    windows = (root, cognition, slm)
    for window in windows:
        try:
            window.attributes("-topmost", True)
        except tk.TclError:
            pass

    # Closing any evaluator window hides that panel only. Runtime remains
    # independent and closing the root is treated as closing all diagnostics.
    cognition.protocol("WM_DELETE_WINDOW", cognition.withdraw)
    slm.protocol("WM_DELETE_WINDOW", slm.withdraw)

    def close_all() -> None:
        for window in (cognition, slm):
            try:
                window.destroy()
            except tk.TclError:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_all)

    def make_header(parent, title_text: str, subtitle_var=None):
        tk.Label(
            parent,
            text=title_text,
            bg=bg,
            fg=fg,
            font=("TkDefaultFont", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        if subtitle_var is not None:
            tk.Label(
                parent,
                textvariable=subtitle_var,
                bg=bg,
                fg=muted,
                font=("TkDefaultFont", 8),
                anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 8))

    def make_metrics(parent, specs):
        frame = tk.Frame(parent, bg=panel, padx=10, pady=8)
        frame.pack(fill="x", padx=12, pady=(0, 8))
        values = {}
        for row, (key, label) in enumerate(specs):
            tk.Label(
                frame,
                text=label,
                bg=panel,
                fg=muted,
                font=("TkDefaultFont", 8),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=1)
            value = tk.StringVar(value="—")
            values[key] = value
            tk.Label(
                frame,
                textvariable=value,
                bg=panel,
                fg=fg,
                font=("TkDefaultFont", 9, "bold"),
                anchor="e",
            ).grid(row=row, column=1, sticky="e", padx=(18, 0), pady=1)
        frame.grid_columnconfigure(1, weight=1)
        return values

    identity_var = tk.StringVar(value="waiting for physics…")
    make_header(root, "SYMBIONT 3D", identity_var)
    runtime_vars = make_metrics(root, (
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
        ("realtime", "Realtime"),
    ))

    outputs_var = tk.StringVar(value="No motor activity yet")
    tk.Label(
        root,
        text="OPAQUE MOTOR ACTIVITY",
        bg=bg,
        fg=cyan,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=14, pady=(2, 2))
    tk.Label(
        root,
        textvariable=outputs_var,
        bg=panel,
        fg=fg,
        font=("TkFixedFont", 9),
        justify="left",
        anchor="nw",
        padx=8,
        pady=6,
    ).pack(fill="x", padx=12, pady=(0, 8))

    make_header(cognition, "BODYSCHEMA & COGNITION")
    cognition_vars = make_metrics(cognition, (
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
        cognition,
        height=225,
        bg=panel,
        highlightthickness=0,
    )
    chart.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    make_header(slm, "PRIVATE SLM")
    slm_vars = make_metrics(slm, (
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

    file_var = tk.StringVar(value="")
    tk.Label(
        slm,
        text="PORTABLE SYMBIONT",
        bg=bg,
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=14, pady=(4, 0))
    tk.Label(
        slm,
        textvariable=file_var,
        bg=bg,
        fg=muted,
        font=("TkDefaultFont", 8),
        justify="left",
        wraplength=390,
        anchor="w",
    ).pack(fill="x", padx=14, pady=(2, 10))

    prediction_history: list[float] = []
    schema_history: list[float] = []
    max_history = 90

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
            chart.create_line(*points, fill=color, width=2, smooth=False)

        series(prediction_history, orange)
        series(schema_history, green)
        chart.create_text(
            pad, height - 10,
            text="prediction error (N/A without predictors)",
            fill=orange, anchor="w", font=("TkDefaultFont", 8),
        )
        chart.create_text(
            pad + 205, height - 10,
            text="body schema",
            fill=green, anchor="w", font=("TkDefaultFont", 8),
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
        runtime_vars["realtime"].set(f"{float(payload['realtime_ratio']):.2f}x")

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
                f"{baseline} {float(baseline_loss):.3f} / {float(candidate_loss):.3f}"
            )
        file_var.set(str(payload["symbiont_file"]))

        if prediction_error is not None:
            prediction_history.append(float(prediction_error))
        schema_history.append(float(payload["schema_confidence"]))
        del prediction_history[:-max_history]
        del schema_history[:-max_history]
        draw_chart()

    def poll() -> None:
        latest = None
        should_close = False
        while True:
            try:
                message = source_queue.get_nowait()
            except queue.Empty:
                break
            if message.get("type") == "close":
                should_close = True
                break
            if message.get("type") == "snapshot":
                latest = message["payload"]

        if should_close:
            close_all()
            return
        if latest is not None:
            apply_snapshot(latest)
        root.after(200, poll)

    root.after(50, poll)
    root.mainloop()


__all__ = [
    "MonitorProcess",
    "MonitorSnapshot",
    "strongest_outputs",
]
