"""Unified Symbiont Lab web application server.

Single canonical entry-point for the local web workbench.
"""

from __future__ import annotations

import argparse
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from symbiont_lab.app.physics3d_runs import DEFAULT_LAB_STATE_ROOT, Physics3DRunStore
from symbiont_lab.app.physics3d_session import Physics3DSession, Physics3DSessionState
from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.observation.demo import DemoOrganismTelemetry
from symbiont_lab.observation.observatory import ObservatorySource
from symbiont_lab.workbench import WEB_ROOT
from symbiont_lab.workbench.runs import (
    ExperimentRunState,
    RunCoordinator,
    StudyRunState,
    start_experiment,
    start_study,
)

from .api import make_handler

_ASSETS = WEB_ROOT


def _default_observatory_dir() -> str | None:
    """Resolve Observatory lazily so the server remains usable without that package."""
    try:
        from observatory.config import DEFAULT_OBSERVATORY_DIR
    except ImportError:
        return None
    return str(DEFAULT_OBSERVATORY_DIR)


class UnifiedLabServer(ThreadingHTTPServer):
    """Local-only HTTP server that owns optional producer lifecycles."""

    daemon_threads = True
    allow_reuse_address = True

    demo_telemetry: DemoOrganismTelemetry | None = None
    physics_session: Physics3DSession | None = None

    def server_close(self) -> None:
        demo = self.demo_telemetry
        self.demo_telemetry = None
        if demo is not None:
            demo.stop()

        session = self.physics_session
        self.physics_session = None
        if session is not None:
            session.close()

        super().server_close()


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    experiment_state: ExperimentRunState | None = None,
    study_state: StudyRunState | None = None,
    observation_bus: ObservationBus | None = None,
    observatory_dir: Path | None = None,
    demo: bool = False,
    physics3d: bool = False,
    physics_state_root: Path | None = None,
) -> UnifiedLabServer:
    """Build the configured server without inventing organism data by default."""
    if host != "127.0.0.1":
        raise ValueError("UnifiedLabServer refuses to bind outside 127.0.0.1")
    if demo and physics3d:
        raise ValueError("demo and physics3d telemetry are mutually exclusive")

    exp_state = experiment_state or ExperimentRunState()
    std_state = study_state or StudyRunState()
    stream = observation_bus or ObservationBus()
    coordinator = RunCoordinator()
    observatory_source = ObservatorySource(observatory_dir)
    run_store = Physics3DRunStore(physics_state_root or DEFAULT_LAB_STATE_ROOT)
    session_holder: dict[str, Physics3DSession | None] = {"physics3d": None}
    server_holder: dict[str, UnifiedLabServer | None] = {"server": None}

    def exp_starter(spec):
        return start_experiment(
            exp_state,
            std_state,
            spec,
            coordinator=coordinator,
        )

    def std_starter(spec, **kw):
        return start_study(
            exp_state,
            std_state,
            spec,
            coordinator=coordinator,
            **kw,
        )

    def start_physics_run(payload: dict[str, Any]) -> dict[str, object]:
        if demo:
            raise RuntimeError("Physics3D cannot start while demo telemetry is enabled")
        if not coordinator.acquire("physics3d"):
            raise RuntimeError("another run is already active")
        try:
            launch = run_store.prepare(payload)
        except Exception:
            coordinator.release("physics3d")
            raise

        session: Physics3DSession

        def on_terminal() -> None:
            snapshot = session.snapshot()
            status = "failed" if snapshot.state == Physics3DSessionState.FAILED else "stopped"
            try:
                run_store.finalize(launch, status=status, error=snapshot.error)
            finally:
                coordinator.release("physics3d")

        session = Physics3DSession(stream, on_terminal=on_terminal)
        session_holder["physics3d"] = session
        server_ref = server_holder["server"]
        if server_ref is not None:
            server_ref.physics_session = session
        run_store.mark_running(launch)
        try:
            if not session.start(launch):
                raise RuntimeError("Physics3D session refused to start")
        except BaseException as exc:
            run_store.finalize(launch, status="failed", error=f"{type(exc).__name__}: {exc}")
            coordinator.release("physics3d")
            raise
        return launch.as_dict()

    def stop_physics_run() -> bool:
        session = session_holder["physics3d"]
        if session is None:
            return False
        snapshot = session.snapshot()
        if snapshot.state in {Physics3DSessionState.STOPPED, Physics3DSessionState.FAILED}:
            return False
        session.request_stop()
        return True

    def source_status() -> dict[str, Any]:
        session = session_holder["physics3d"]
        return {
            "run_coordinator": coordinator.payload(),
            "organism_stream": {
                "available": True,
                "has_data": stream.has_data,
                "latest_sequence": stream.latest_sequence,
            },
            "observatory": {
                "configured": observatory_dir is not None,
                "available": observatory_source.available,
            },
            "physics3d": (
                session.snapshot().as_dict()
                if session is not None
                else {
                    "state": "disabled",
                    "exit_code": None,
                    "error": None,
                    "traceback": None,
                    "thread_alive": False,
                }
            ),
            "demo": {"enabled": bool(demo)},
        }

    server = UnifiedLabServer(
        (host, port),
        make_handler(
            exp_state,
            std_state,
            exp_starter,
            std_starter,
            stream,
            observatory_dir,
            _ASSETS,
            source_status=source_status,
            body_catalog=run_store.bodies,
            organism_catalog=run_store.organisms,
            run_catalog=run_store.runs,
            physics_run_starter=start_physics_run,
            physics_run_stopper=stop_physics_run,
        ),
    )
    server_holder["server"] = server

    if demo:
        demo_telemetry = DemoOrganismTelemetry(stream)
        demo_telemetry.start()
        server.demo_telemetry = demo_telemetry

    if physics3d:
        if not coordinator.acquire("physics3d"):
            server.server_close()
            raise RuntimeError("another run is already active")
        session = Physics3DSession(
            stream,
            on_terminal=lambda: coordinator.release("physics3d"),
        )
        session_holder["physics3d"] = session
        server.physics_session = session
        try:
            session.start()
        except BaseException:
            coordinator.release("physics3d")
            server.server_close()
            raise

    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="symbiont-lab",
        description="Symbiont Lab — unified local workbench",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--archive", default=".symbiont/experiments.jsonl")
    parser.add_argument("--study-archive", default=".symbiont/studies.jsonl")
    parser.add_argument("--no-record", action="store_true", help="Disable experiment archiving")
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Emit synthetic organism telemetry for UI development only",
    )
    parser.add_argument(
        "--physics3d",
        action="store_true",
        help="Run the canonical Physics3D embodiment and stream it into the web UI",
    )
    parser.add_argument(
        "--observatory-dir",
        default=_default_observatory_dir(),
        metavar="DIR",
        help="Observatory state directory used by live Mind data",
    )
    args = parser.parse_args(argv)

    archive = None if args.no_record else ExperimentArchive(args.archive)
    study_archive = None if args.no_record else StudyArchive(args.study_archive)
    obs_dir = Path(args.observatory_dir).expanduser() if args.observatory_dir else None

    exp_state = ExperimentRunState(archive=archive)
    std_state = StudyRunState(archive=study_archive)
    stream = ObservationBus()

    server = make_server(
        port=args.port,
        experiment_state=exp_state,
        study_state=std_state,
        observation_bus=stream,
        observatory_dir=obs_dir,
        demo=args.demo,
        physics3d=args.physics3d,
    )
    url = f"http://127.0.0.1:{args.port}"
    print(f"Symbiont Lab  →  {url}")
    if archive:
        print(f"Archive       →  {archive.path}")
    if obs_dir:
        print(f"Observatory   →  {obs_dir}")
    if args.demo:
        print("Telemetry     →  DEMO (synthetic, UI development only)")
    if args.physics3d:
        print("Telemetry     →  Physics3D canonical embodiment")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
