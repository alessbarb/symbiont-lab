from __future__ import annotations
import multiprocessing as mp
from pathlib import Path
import queue
import traceback
from typing import Any
from .models import RunDescriptor, RunKind, RunStatus

def _run_experiment_worker(spec_path: str, event_queue) -> None:
    try:
        from symbiont_lab.experiments.loader import load_experiment_file
        from symbiont_lab.experiments.runner import ExperimentRunner
        spec = load_experiment_file(spec_path)
        event_queue.put({"type":"status","status":RunStatus.RUNNING.value,"detail":f"Running {spec.protocol}"})
        def progress(ev: Any) -> None:
            step = getattr(ev, "step", None)
            if step is not None:
                event_queue.put({"type":"progress","detail":f"step {int(step):,}"})
        _, manifest, run_dir = ExperimentRunner().run(spec, progress_cb=progress)
        event_queue.put({"type":"completed","status":RunStatus.COMPLETED.value,
                         "detail":f"Completed {manifest.run_id}","artifact_path":str(run_dir)})
    except BaseException as exc:
        event_queue.put({"type":"failed","status":RunStatus.FAILED.value,
                         "detail":f"{type(exc).__name__}: {exc}","traceback":traceback.format_exc()})

def _run_physics3d_worker(event_queue, frame_queue, command_queue) -> None:
    try:
        from symbiont_lab.app.physics3d_monitor import QueueViewerBridge
        from symbiont_lab.physics3d.cli import run
        bridge = QueueViewerBridge(frame_queue, command_queue)
        event_queue.put({"type":"status","status":RunStatus.RUNNING.value,"detail":"Physics3D running"})
        code = run(show_monitor=True, headless=False, viewer_bridge=bridge)
        event_queue.put({"type":"completed","status":RunStatus.COMPLETED.value,
                         "detail":f"Physics3D stopped (exit {code})"})
    except BaseException as exc:
        event_queue.put({"type":"failed","status":RunStatus.FAILED.value,
                         "detail":f"{type(exc).__name__}: {exc}","traceback":traceback.format_exc()})

class RunController:
    """Supervise one foreground scientific run without blocking Tk."""
    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._process: mp.Process | None = None
        self._events = None
        self.physics_frame_queue = None
        self.physics_command_queue = None
        self.current: RunDescriptor | None = None

    @property
    def busy(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def launch_experiment(self, spec_path: str | Path) -> RunDescriptor:
        if self.busy:
            raise RuntimeError("another run is already active")
        path = Path(spec_path)
        self._events = self._ctx.Queue()
        self.current = RunDescriptor(RunKind.EXPERIMENT, path.parent.name, RunStatus.STARTING, str(path))
        self._process = self._ctx.Process(target=_run_experiment_worker,args=(str(path),self._events),
                                          name=f"symbiont-experiment-{path.parent.name}")
        self._process.start()
        return self.current

    def launch_physics3d(self) -> RunDescriptor:
        if self.busy:
            raise RuntimeError("another run is already active")
        self._events = self._ctx.Queue()
        self.physics_frame_queue = self._ctx.Queue(maxsize=2)
        self.physics_command_queue = self._ctx.Queue(maxsize=16)
        self.current = RunDescriptor(RunKind.PHYSICS3D,"Physics3D",RunStatus.STARTING,
                                     "Starting canonical 3D embodiment")
        self._process = self._ctx.Process(
            target=_run_physics3d_worker,
            args=(self._events, self.physics_frame_queue, self.physics_command_queue),
            name="symbiont-physics3d",
        )
        self._process.start()
        return self.current

    def stop(self) -> None:
        if not self.busy or self._process is None:
            return
        if self.current is not None:
            self.current.status = RunStatus.STOPPING
            self.current.detail = "Stopping gracefully"
        self._process.terminate()

    def poll(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if self._events is not None:
            while True:
                try:
                    event = self._events.get_nowait()
                except queue.Empty:
                    break
                events.append(event)
                if self.current is not None:
                    if event.get("status"):
                        self.current.status = RunStatus(event["status"])
                    if event.get("detail"):
                        self.current.detail = str(event["detail"])
                    if event.get("artifact_path"):
                        self.current.artifact_path = str(event["artifact_path"])
        if self._process is not None and not self._process.is_alive():
            self._process.join(timeout=0.1)
            if self.current is not None and self.current.status in {RunStatus.STARTING,RunStatus.RUNNING,RunStatus.STOPPING}:
                self.current.status = RunStatus.STOPPED if self.current.status == RunStatus.STOPPING else RunStatus.FAILED
            self._process = None
        return events
