"""Unified Symbiont Lab web application server.

Single canonical entry-point for the local web workbench.

Usage:
  symbiont-lab                   # launch + open browser
  symbiont-lab --no-browser      # launch only
  symbiont-lab --demo            # explicit synthetic telemetry for UI development
"""
from __future__ import annotations

import argparse
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from .api import make_handler
from symbiont_lab.observation.demo import DemoOrganismTelemetry
from symbiont_lab.observation.physics3d import Physics3DObservationBridge
from .organism_stream import OrganismStream
from .state import DashboardState, StudyDashboardState, start_experiment, start_study

_ASSETS = Path(__file__).parent / "assets"


def _default_observatory_dir() -> str | None:
    """Resolve Observatory lazily so the server remains usable without that package."""
    try:
        from observatory.config import DEFAULT_OBSERVATORY_DIR
    except ImportError:
        return None
    return str(DEFAULT_OBSERVATORY_DIR)


class UnifiedLabServer(ThreadingHTTPServer):
    """Local-only HTTP server that owns optional telemetry producer lifecycles."""

    daemon_threads = True
    allow_reuse_address = True

    demo_telemetry: DemoOrganismTelemetry | None = None
    physics_bridge: Physics3DObservationBridge | None = None
    physics_thread: threading.Thread | None = None

    def server_close(self) -> None:
        demo = self.demo_telemetry
        self.demo_telemetry = None
        if demo is not None:
            demo.stop()

        bridge = self.physics_bridge
        thread = self.physics_thread
        self.physics_bridge = None
        self.physics_thread = None
        if bridge is not None:
            bridge.request_stop()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

        super().server_close()


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    experiment_state: DashboardState | None = None,
    study_state: StudyDashboardState | None = None,
    organism_stream: OrganismStream | None = None,
    observatory_dir: Path | None = None,
    demo: bool = False,
    physics3d: bool = False,
) -> UnifiedLabServer:
    """Build the configured server without inventing organism data by default."""
    if host != "127.0.0.1":
        raise ValueError("UnifiedLabServer refuses to bind outside 127.0.0.1")

    exp_state = experiment_state or DashboardState()
    std_state = study_state or StudyDashboardState()
    stream = organism_stream or OrganismStream()

    exp_starter = lambda spec: start_experiment(exp_state, std_state, spec)
    std_starter = lambda spec, **kw: start_study(exp_state, std_state, spec, **kw)

    server = UnifiedLabServer(
        (host, port),
        make_handler(exp_state, std_state, exp_starter, std_starter, stream, observatory_dir, _ASSETS),
    )
    if demo and physics3d:
        server.server_close()
        raise ValueError("demo and physics3d telemetry are mutually exclusive")

    if demo:
        demo_telemetry = DemoOrganismTelemetry(stream)
        demo_telemetry.start()
        server.demo_telemetry = demo_telemetry

    if physics3d:
        from symbiont_lab.physics3d.cli import run as run_physics3d

        bridge = Physics3DObservationBridge(stream)

        def run_embodiment() -> None:
            try:
                run_physics3d(
                    show_monitor=True,
                    headless=False,
                    viewer_bridge=bridge,
                )
            finally:
                bridge.close()

        thread = threading.Thread(
            target=run_embodiment,
            daemon=True,
            name="symbiont-lab-physics3d",
        )
        server.physics_bridge = bridge
        server.physics_thread = thread
        thread.start()

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
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
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

    exp_state = DashboardState(archive=archive)
    std_state = StudyDashboardState(archive=study_archive)
    stream = OrganismStream()

    server = make_server(
        port=args.port,
        experiment_state=exp_state,
        study_state=std_state,
        organism_stream=stream,
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
