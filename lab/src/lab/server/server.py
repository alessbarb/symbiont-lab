"""Unified Symbiont Lab web application server.

Single canonical entry-point for the local web workbench.
"""

from __future__ import annotations

import argparse
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from lab.app.physics3d.runs import DEFAULT_LAB_STATE_ROOT, Physics3DRunStore
from lab.app.physics3d.session import Physics3DSession, Physics3DSessionState
from lab.experience import resolve_termination
from lab.observation.bus import ObservationBus
from lab.observation.observatory import ObservatorySource
from lab.observation.provenance_journal import ProvenanceIndex, ProvenanceJournal
from lab.server.api import make_handler
from lab.workbench import WEB_ROOT
from lab.workbench.coordinator import RunCoordinator
from symbiont.provenance import CausalRef

_ASSETS = WEB_ROOT


def _default_observatory_dir() -> str | None:
    """Resolve Observatory lazily so the server remains usable without that package."""
    try:
        from lab.observatory.config import DEFAULT_OBSERVATORY_DIR
    except ImportError:
        return None
    return str(DEFAULT_OBSERVATORY_DIR)


class UnifiedLabServer(ThreadingHTTPServer):
    """Local-only HTTP server that owns optional producer lifecycles."""

    daemon_threads = True
    allow_reuse_address = True

    physics_session: Physics3DSession | None = None

    def server_close(self) -> None:
        session = self.physics_session
        self.physics_session = None
        if session is not None:
            session.close()

        super().server_close()


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    observation_bus: ObservationBus | None = None,
    observatory_dir: Path | None = None,
    physics3d: bool = False,
    physics_state_root: Path | None = None,
) -> UnifiedLabServer:
    """Build the configured server without inventing organism data by default."""
    if host != "127.0.0.1":
        raise ValueError("UnifiedLabServer refuses to bind outside 127.0.0.1")

    stream = observation_bus or ObservationBus()
    coordinator = RunCoordinator()
    observatory_source = ObservatorySource(observatory_dir)
    run_store = Physics3DRunStore(physics_state_root or DEFAULT_LAB_STATE_ROOT)
    session_holder: dict[str, Physics3DSession | None] = {"physics3d": None}
    server_holder: dict[str, UnifiedLabServer | None] = {"server": None}

    def start_physics_run(payload: dict[str, Any]) -> dict[str, object]:
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
            failed = snapshot.state == Physics3DSessionState.FAILED
            status = "failed" if failed else "stopped"
            reason = resolve_termination(launch.run_kind, snapshot.exit_cause, failed=failed)
            try:
                run_store.finalize(
                    launch,
                    status=status,
                    error=snapshot.error,
                    termination_reason=reason.value,
                    protection_breach=(
                        launch.run_kind.is_acquisition and reason.value == "body_non_viable"
                    ),
                )
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
            run_store.finalize(
                launch,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                termination_reason="technical_failure",
            )
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

    def causal_provenance_query(kind: str, ref_id: str, depth: int) -> dict[str, Any] | None:
        """Read causal history for the current managed run; apparatus only."""
        session = session_holder["physics3d"]
        if session is None:
            return None
        run_id = session.snapshot().run_id
        if not run_id:
            return None
        journal_path = run_store.runs_dir / run_id / "provenance.jsonl"
        if not journal_path.is_file():
            return None
        index = ProvenanceIndex.load(ProvenanceJournal(journal_path))
        ref = CausalRef(kind, ref_id)
        if ref not in index.lifecycle:
            # A root reference can legitimately lack a producer; only return
            # such a tree when it is mentioned by some recorded event.
            mentioned = any(
                ref == event.subject or ref in event.produced or ref in event.caused_by
                for event in index.events
            )
            if not mentioned:
                return None
        return {
            "run_id": run_id,
            "reference": ref.payload(),
            "tree": index.why(ref, depth=depth),
        }

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
                {
                    **session.snapshot().as_dict(),
                    # Observer-only human name; Symbiont never sees it.
                    "organism_alias": run_store.alias_for(session.snapshot().organism_ref),
                }
                if session is not None
                else {
                    "state": "disabled",
                    "exit_code": None,
                    "error": None,
                    "traceback": None,
                    "thread_alive": False,
                }
            ),
        }

    server = UnifiedLabServer(
        (host, port),
        make_handler(
            stream,
            observatory_dir,
            _ASSETS,
            source_status=source_status,
            body_catalog=run_store.bodies,
            organism_catalog=run_store.organisms,
            run_catalog=run_store.runs,
            physics_run_starter=start_physics_run,
            physics_run_stopper=stop_physics_run,
            organism_alias_setter=run_store.set_alias,
            causal_provenance_query=causal_provenance_query,
        ),
    )
    server_holder["server"] = server

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
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
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

    obs_dir = Path(args.observatory_dir).expanduser() if args.observatory_dir else None

    stream = ObservationBus()

    server = make_server(
        port=args.port,
        observation_bus=stream,
        observatory_dir=obs_dir,
        physics3d=args.physics3d,
    )
    url = f"http://127.0.0.1:{args.port}"
    print(f"Symbiont Lab  →  {url}")
    if obs_dir:
        print(f"Observatory   →  {obs_dir}")
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
