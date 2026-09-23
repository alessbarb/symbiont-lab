"""Supervised application service for the canonical Physics3D embodiment."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
import traceback
from typing import Any, Callable

from symbiont_lab.app.physics3d_runs import Physics3DLaunchSpec
from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.observation.physics3d import Physics3DObservationBridge


class Physics3DSessionState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class Physics3DSessionSnapshot:
    state: Physics3DSessionState
    exit_code: int | None
    error: str | None
    traceback: str | None
    thread_alive: bool
    run_id: str | None = None
    organism_ref: str | None = None
    body_kind: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "exit_code": self.exit_code,
            "error": self.error,
            "traceback": self.traceback,
            "thread_alive": self.thread_alive,
            "run_id": self.run_id,
            "organism_ref": self.organism_ref,
            "body_kind": self.body_kind,
        }


class Physics3DSession:
    """Own one Physics3D lifecycle and expose only application-level controls.

    The HTTP server and desktop depend on this service boundary rather than the
    command-line adapter. The canonical execution loop lives in
    ``symbiont_lab.physics3d.engine``.
    """

    def __init__(
        self,
        observation_bus: ObservationBus,
        *,
        runner: Callable[..., int] | None = None,
        on_terminal: Callable[[], None] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._bus = observation_bus
        self._runner = runner
        self._on_terminal = on_terminal
        self._bridge: Physics3DObservationBridge | None = None
        self._thread: threading.Thread | None = None
        self._state = Physics3DSessionState.IDLE
        self._exit_code: int | None = None
        self._error: str | None = None
        self._traceback: str | None = None
        self._launch: Physics3DLaunchSpec | None = None

    def start(self, launch: Physics3DLaunchSpec | None = None) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._bridge = Physics3DObservationBridge(self._bus)
            self._state = Physics3DSessionState.STARTING
            self._exit_code = None
            self._error = None
            self._traceback = None
            self._launch = launch
            thread = threading.Thread(
                target=self._run,
                args=(launch,),
                daemon=True,
                name="symbiont-lab-physics3d",
            )
            self._thread = thread
            try:
                thread.start()
            except BaseException as exc:
                self._state = Physics3DSessionState.FAILED
                self._error = f"{type(exc).__name__}: {exc}"
                self._traceback = traceback.format_exc()
                self._bridge.close()
                self._bridge = None
                self._thread = None
                raise
            return True

    def _run(self, launch: Physics3DLaunchSpec | None) -> None:
        bridge = self._bridge
        if bridge is None:
            return
        try:
            runner = self._runner
            if runner is None:
                from symbiont_lab.physics3d.engine import run as runner

            with self._lock:
                if self._state != Physics3DSessionState.STOPPING:
                    self._state = Physics3DSessionState.RUNNING
            runner_kwargs: dict[str, object] = {
                "show_monitor": True,
                "headless": False,
                "viewer_bridge": bridge,
            }
            if launch is not None:
                runner_kwargs.update(launch.runner_kwargs())
            code = runner(**runner_kwargs)
            with self._lock:
                self._exit_code = int(code)
                if self._state == Physics3DSessionState.STOPPING:
                    self._state = Physics3DSessionState.STOPPED
                elif code == 0:
                    self._state = Physics3DSessionState.STOPPED
                else:
                    self._state = Physics3DSessionState.FAILED
                    self._error = f"Physics3D exited with code {code}"
        except BaseException as exc:
            with self._lock:
                self._state = Physics3DSessionState.FAILED
                self._error = f"{type(exc).__name__}: {exc}"
                self._traceback = traceback.format_exc()
        finally:
            bridge.close()
            callback = self._on_terminal
            if callback is not None:
                callback()

    def request_stop(self) -> None:
        with self._lock:
            bridge = self._bridge
            thread = self._thread
            terminal = self._state in {
                Physics3DSessionState.FAILED,
                Physics3DSessionState.STOPPED,
            }
            if thread is None or not thread.is_alive():
                if not terminal:
                    self._state = Physics3DSessionState.STOPPED
                return
            if not terminal:
                self._state = Physics3DSessionState.STOPPING
        if bridge is not None:
            bridge.request_stop()

    def close(self, *, timeout: float = 5.0) -> None:
        self.request_stop()
        with self._lock:
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        with self._lock:
            if thread is not None and thread.is_alive():
                self._state = Physics3DSessionState.FAILED
                self._error = "Physics3D did not stop before shutdown timeout"
            self._bridge = None

    def snapshot(self) -> Physics3DSessionSnapshot:
        with self._lock:
            thread = self._thread
            launch = self._launch
            return Physics3DSessionSnapshot(
                state=self._state,
                exit_code=self._exit_code,
                error=self._error,
                traceback=self._traceback,
                thread_alive=bool(thread and thread.is_alive()),
                run_id=launch.run_id if launch is not None else None,
                organism_ref=launch.organism_ref if launch is not None else None,
                body_kind=launch.body_kind if launch is not None else None,
            )


__all__ = [
    "Physics3DSession",
    "Physics3DSessionSnapshot",
    "Physics3DSessionState",
]
