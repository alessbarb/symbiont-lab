"""Unified Symbiont Lab web application server.

Single entry-point that replaces:
  - symbiont_lab.dashboard.server  (experiment / study dashboard)
  - observatory.server             (organism journal SSE)
  - symbiont_lab.app               (Tkinter desktop app)

Usage:
  symbiont-lab                   # launch + open browser
  symbiont-lab --no-browser      # launch only
"""
from __future__ import annotations

import argparse
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.dashboard.state import DashboardState, StudyDashboardState
from symbiont_lab.dashboard.state import start_experiment, start_study

from .api import make_handler
from .organism_stream import DemoOrganismTelemetry, OrganismStream

_ASSETS = Path(__file__).parent / "assets"


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    experiment_state: DashboardState | None = None,
    study_state: StudyDashboardState | None = None,
    organism_stream: OrganismStream | None = None,
    observatory_dir: Path | None = None,
) -> ThreadingHTTPServer:
    """Build and return the configured ThreadingHTTPServer (not started yet)."""
    exp_state = experiment_state or DashboardState()
    std_state = study_state or StudyDashboardState()
    stream = organism_stream or OrganismStream()

    exp_starter = lambda spec: start_experiment(exp_state, std_state, spec)
    std_starter = lambda spec, **kw: start_study(exp_state, std_state, spec, **kw)

    demo = DemoOrganismTelemetry(stream)
    demo.start()

    server = ThreadingHTTPServer(
        (host, port),
        make_handler(exp_state, std_state, exp_starter, std_starter, stream, observatory_dir, _ASSETS),
    )
    server.daemon_threads = True
    server.allow_reuse_address = True
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
        "--observatory-dir",
        default=None,
        metavar="DIR",
        help="Observatory state directory — enables live Mind view data",
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
    )
    url = f"http://127.0.0.1:{args.port}"
    print(f"Symbiont Lab  →  {url}")
    if archive:
        print(f"Archive       →  {archive.path}")
    if obs_dir:
        print(f"Observatory   →  {obs_dir}")
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
