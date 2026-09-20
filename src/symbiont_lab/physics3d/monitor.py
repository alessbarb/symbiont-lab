"""Separate lightweight monitor window for Physics3D.

The monitor runs in its own process and receives evaluator-only snapshots through
a bounded multiprocessing queue. It never imports PyBullet and has no path back
into cognition or physics.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from multiprocessing.context import BaseContext
from pathlib import Path
import queue
from typing import Mapping


@dataclass(frozen=True, slots=True)
class MonitorSnapshot:
    tick: int
    symbiont_id: str
    embodiment_mode: str
    schema_confidence: float
    schema_parts: int
    schema_dependencies: int
    prediction_error: float
    active_effectors: int
    joint_motion: float
    contact_count: int
    height: float
    checkpoint_age: int
    symbiont_file: str
    strongest_outputs: tuple[tuple[str, float], ...]
    slm_records: int
    slm_models: int
    slm_active: bool
    slm_training: bool
    slm_error: str | None


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
    """Small lifecycle wrapper around the external Tkinter monitor."""

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

    root = tk.Tk()
    root.title("Symbiont 3D — Monitor")
    root.geometry("430x720")
    root.minsize(390, 600)
    root.configure(bg="#11161c")

    fg = "#e8eef5"
    muted = "#93a4b8"
    cyan = "#73d7d2"
    orange = "#ee936f"
    green = "#79d894"
    panel = "#18212b"

    title = tk.Label(
        root,
        text="SYMBIONT 3D",
        bg="#11161c",
        fg=fg,
        font=("TkDefaultFont", 16, "bold"),
        anchor="w",
    )
    title.pack(fill="x", padx=16, pady=(14, 2))

    identity_var = tk.StringVar(value="waiting for physics…")
    identity = tk.Label(
        root,
        textvariable=identity_var,
        bg="#11161c",
        fg=muted,
        font=("TkDefaultFont", 9),
        anchor="w",
    )
    identity.pack(fill="x", padx=16, pady=(0, 12))

    metrics_frame = tk.Frame(root, bg=panel, padx=12, pady=10)
    metrics_frame.pack(fill="x", padx=14, pady=(0, 10))

    metric_vars: dict[str, tk.StringVar] = {}
    metric_names = (
        ("tick", "Tick"),
        ("mode", "Embodiment"),
        ("schema", "BodySchema confidence"),
        ("schema_parts", "BodySchema parts"),
        ("schema_deps", "BodySchema dependencies"),
        ("error", "Prediction error"),
        ("outputs", "Active outputs"),
        ("motion", "Joint motion"),
        ("contacts", "Contacts"),
        ("height", "Body height"),
        ("checkpoint", "Checkpoint age"),
        ("slm_records", "SLM experiences"),
        ("slm_models", "SLM models"),
        ("slm_active", "SLM active"),
        ("slm_training", "SLM training"),
        ("slm_error", "SLM status"),
    )
    for row, (key, label) in enumerate(metric_names):
        tk.Label(
            metrics_frame,
            text=label,
            bg=panel,
            fg=muted,
            font=("TkDefaultFont", 9),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=2)
        variable = tk.StringVar(value="—")
        metric_vars[key] = variable
        tk.Label(
            metrics_frame,
            textvariable=variable,
            bg=panel,
            fg=fg,
            font=("TkDefaultFont", 10, "bold"),
            anchor="e",
        ).grid(row=row, column=1, sticky="e", padx=(20, 0), pady=2)
    metrics_frame.grid_columnconfigure(1, weight=1)

    outputs_var = tk.StringVar(value="No motor activity yet")
    tk.Label(
        root,
        text="OPAQUE OUTPUT ACTIVITY",
        bg="#11161c",
        fg=cyan,
        font=("TkDefaultFont", 9, "bold"),
        anchor="w",
    ).pack(fill="x", padx=16, pady=(4, 2))
    tk.Label(
        root,
        textvariable=outputs_var,
        bg=panel,
        fg=fg,
        font=("TkFixedFont", 10),
        justify="left",
        anchor="nw",
        padx=10,
        pady=8,
    ).pack(fill="x", padx=14, pady=(0, 10))

    chart = tk.Canvas(
        root,
        height=210,
        bg=panel,
        highlightthickness=0,
    )
    chart.pack(fill="x", padx=14, pady=(0, 10))

    file_var = tk.StringVar(value="")
    tk.Label(
        root,
        text="PORTABLE SYMBIONT",
        bg="#11161c",
        fg=muted,
        font=("TkDefaultFont", 8, "bold"),
        anchor="w",
    ).pack(fill="x", padx=16)
    tk.Label(
        root,
        textvariable=file_var,
        bg="#11161c",
        fg=muted,
        font=("TkDefaultFont", 8),
        justify="left",
        wraplength=390,
        anchor="w",
    ).pack(fill="x", padx=16, pady=(2, 12))

    prediction_history: list[float] = []
    schema_history: list[float] = []
    max_history = 90

    def draw_chart() -> None:
        chart.delete("all")
        width = max(1, chart.winfo_width())
        height = max(1, chart.winfo_height())
        pad = 28
        graph_w = max(1, width - pad * 2)
        graph_h = max(1, height - 52)

        chart.create_text(
            pad,
            12,
            text="rolling learning signals",
            fill=muted,
            anchor="w",
            font=("TkDefaultFont", 8),
        )
        chart.create_line(pad, 30, pad, 30 + graph_h, fill="#354252")
        chart.create_line(
            pad, 30 + graph_h, pad + graph_w, 30 + graph_h, fill="#354252"
        )

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
            pad,
            height - 10,
            text="prediction error",
            fill=orange,
            anchor="w",
            font=("TkDefaultFont", 8),
        )
        chart.create_text(
            pad + 120,
            height - 10,
            text="body-schema confidence",
            fill=green,
            anchor="w",
            font=("TkDefaultFont", 8),
        )

    def apply_snapshot(payload: dict) -> None:
        identity_var.set(f"{payload['symbiont_id']}  ·  passive evaluator view")
        metric_vars["tick"].set(f"{int(payload['tick']):,}")
        metric_vars["mode"].set(str(payload["embodiment_mode"]))
        metric_vars["schema"].set(f"{float(payload['schema_confidence']):.3f}")
        metric_vars["schema_parts"].set(str(int(payload["schema_parts"])))
        metric_vars["schema_deps"].set(str(int(payload["schema_dependencies"])))
        metric_vars["error"].set(f"{float(payload['prediction_error']):.3f}")
        metric_vars["outputs"].set(str(int(payload["active_effectors"])))
        metric_vars["motion"].set(f"{float(payload['joint_motion']):.2f}")
        metric_vars["contacts"].set(str(int(payload["contact_count"])))
        metric_vars["height"].set(f"{float(payload['height']):+.3f} m")
        metric_vars["checkpoint"].set(f"{int(payload['checkpoint_age']):,} ticks")
        metric_vars["slm_records"].set(f"{int(payload['slm_records']):,}")
        metric_vars["slm_models"].set(str(int(payload["slm_models"])))
        metric_vars["slm_active"].set("yes" if payload["slm_active"] else "no")
        metric_vars["slm_training"].set("yes" if payload["slm_training"] else "no")
        metric_vars["slm_error"].set(str(payload["slm_error"] or "ok"))

        strongest = payload.get("strongest_outputs", ())
        outputs_var.set(
            "\n".join(
                f"{str(channel):<9} {float(value):.3f}"
                for channel, value in strongest
            )
            or "No motor activity yet"
        )
        file_var.set(str(payload["symbiont_file"]))

        prediction_history.append(float(payload["prediction_error"]))
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
            root.destroy()
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
