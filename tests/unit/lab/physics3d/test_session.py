from __future__ import annotations

import threading

from symbiont_lab.app.physics3d_runs import Physics3DLaunchSpec
from symbiont_lab.app.physics3d_session import (
    Physics3DSession,
    Physics3DSessionState,
)
from symbiont_lab.observation.bus import ObservationBus


def test_physics3d_session_supervises_clean_stop_without_pybullet() -> None:
    started = threading.Event()
    release = threading.Event()
    terminal = threading.Event()

    def runner(**kwargs) -> int:
        assert kwargs["show_monitor"] is True
        assert kwargs["headless"] is False
        assert kwargs["viewer_bridge"] is not None
        started.set()
        assert release.wait(timeout=2.0)
        return 0

    session = Physics3DSession(
        ObservationBus(),
        runner=runner,
        on_terminal=terminal.set,
    )
    assert session.start() is True
    assert started.wait(timeout=2.0)
    assert session.snapshot().state == Physics3DSessionState.RUNNING

    session.request_stop()
    assert session.snapshot().state == Physics3DSessionState.STOPPING
    release.set()
    assert terminal.wait(timeout=2.0)
    session.close(timeout=2.0)

    snapshot = session.snapshot()
    assert snapshot.state == Physics3DSessionState.STOPPED
    assert snapshot.exit_code == 0
    assert snapshot.error is None
    assert snapshot.thread_alive is False


def test_physics3d_session_surfaces_runner_failure() -> None:
    terminal = threading.Event()

    def runner(**kwargs) -> int:
        raise RuntimeError("synthetic runner failure")

    session = Physics3DSession(
        ObservationBus(),
        runner=runner,
        on_terminal=terminal.set,
    )
    assert session.start() is True
    assert terminal.wait(timeout=2.0)
    session.close(timeout=2.0)

    snapshot = session.snapshot()
    assert snapshot.state == Physics3DSessionState.FAILED
    assert snapshot.exit_code is None
    assert snapshot.error == "RuntimeError: synthetic runner failure"
    assert "synthetic runner failure" in (snapshot.traceback or "")
    assert snapshot.thread_alive is False


def test_physics3d_session_passes_managed_launch_to_runner(tmp_path) -> None:
    captured = {}
    terminal = threading.Event()

    def runner(**kwargs) -> int:
        captured.update(kwargs)
        return 0

    launch = Physics3DLaunchSpec(
        run_id="run-test",
        organism_ref="org-test",
        body_ref="body-test",
        body_kind="anthropomorphic-v5",
        organism_mode="existing",
        body_mode="fresh",
        symbiont_file=tmp_path / "organism.symbiont",
        body_file=tmp_path / "body.json",
        telemetry_file=tmp_path / "telemetry",
    )
    session = Physics3DSession(ObservationBus(), runner=runner, on_terminal=terminal.set)
    assert session.start(launch) is True
    assert terminal.wait(timeout=2.0)
    session.close(timeout=2.0)

    assert captured["body_kind"] == "anthropomorphic-v5"
    assert captured["fresh_body"] is True
    assert captured["new_symbiont"] is False
    assert captured["symbiont_file"] == launch.symbiont_file
    snapshot = session.snapshot()
    assert snapshot.run_id == "run-test"
    assert snapshot.organism_ref == "org-test"
