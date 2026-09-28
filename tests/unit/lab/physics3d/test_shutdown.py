from __future__ import annotations

from types import SimpleNamespace

import pytest

from symbiont_lab.physics3d import cli, engine
from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime


class _FakeSignalKnowledge:
    def __init__(self, tick: int) -> None:
        self._tick = tick

    def checkpoint(self):
        return {"last_tick": self._tick}


class _FakeRuntimeForSave:
    def __init__(self, *, tick: int = 123, physical_error: Exception | None = None) -> None:
        self.tick_count = tick
        self.organism = SimpleNamespace(signal_knowledge=_FakeSignalKnowledge(tick))
        self._physical_error = physical_error

    def checkpoint(self, *, lifecycle_state="active"):
        return {
            "saved_at_tick": self.tick_count,
            "organism_id": "test",
            "lifecycle_state": lifecycle_state,
        }

    def physical_checkpoint(self):
        if self._physical_error is not None:
            raise self._physical_error
        return ({"schema_version": 1}, self.tick_count)


def test_checkpoint_saves_portable_symbiont_before_reading_physics(monkeypatch, tmp_path):
    events: list[str] = []

    def save_bundle(payload, models_dir, path):
        events.append("symbiont")
        return path

    def save_body(payload, path):
        events.append("body")
        return path

    monkeypatch.setattr(engine, "save_symbiont_bundle", save_bundle)
    monkeypatch.setattr(engine, "save_body_state_file", save_body)

    runtime = _FakeRuntimeForSave(physical_error=RuntimeError("physics server already closed"))

    with pytest.raises(RuntimeError, match="physics server already closed"):
        engine._save_checkpoint(
            runtime,
            symbiont_file=tmp_path / "subject.symbiont",
            body_file=tmp_path / "body.json",
            models_dir=tmp_path / "models",
        )

    assert events == ["symbiont"]


def test_checkpoint_writes_body_with_its_own_completed_tick(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        engine,
        "save_symbiont_bundle",
        lambda payload, models_dir, path: path,
    )

    def save_body(payload, path):
        captured.update(payload)
        return path

    monkeypatch.setattr(engine, "save_body_state_file", save_body)

    runtime = _FakeRuntimeForSave(tick=321)
    engine._save_checkpoint(
        runtime,
        symbiont_file=tmp_path / "subject.symbiont",
        body_file=tmp_path / "body.json",
        models_dir=tmp_path / "models",
    )

    assert captured["symbiont_ticks"] == 321


def test_runtime_close_is_idempotent_after_native_server_disconnect():
    class FakeBullet:
        def __init__(self):
            self.disconnect_calls = 0

        def isConnected(self, *, physicsClientId):
            return 0

        def disconnect(self, *, physicsClientId):
            self.disconnect_calls += 1
            raise AssertionError("disconnect must not be called for dead server")

    runtime = PyBulletEmbodimentRuntime.__new__(PyBulletEmbodimentRuntime)
    runtime.p = FakeBullet()
    runtime.client_id = 7

    runtime.close()
    runtime.close()

    assert runtime.client_id == -1
    assert runtime.p.disconnect_calls == 0


def test_new_subject_archives_existing_artifacts(tmp_path):
    symbiont = tmp_path / "subject.symbiont"
    body = tmp_path / "subject.body-v4.json"
    telemetry = tmp_path / "subject.telemetry-v2.ndjson"
    symbiont.write_bytes(b"mind")
    body.write_text("body", encoding="utf-8")
    telemetry.write_text("telemetry", encoding="utf-8")

    archived = engine._archive_existing_subject(
        symbiont_file=symbiont,
        body_file=body,
        telemetry_file=telemetry,
    )

    assert archived is not None
    assert (archived / symbiont.name).read_bytes() == b"mind"
    assert (archived / body.name).read_text(encoding="utf-8") == "body"
    assert (archived / telemetry.name).read_text(encoding="utf-8") == "telemetry"
    assert not symbiont.exists()
    assert not body.exists()
    assert not telemetry.exists()


def test_cli_defers_sigint_instead_of_raising_inside_tick():
    import inspect

    source = inspect.getsource(cli.run)
    assert '("SIGINT", "SIGTERM", "SIGHUP")' in source
    assert "stop_requested = True" in source
    assert "threading.current_thread() is threading.main_thread()" in source
    assert "if owns_signal_handlers:" in source


def test_new_subject_preserves_v3_telemetry_history(tmp_path):
    symbiont = tmp_path / "subject.symbiont"
    body = tmp_path / "subject.body-v4.json"
    telemetry_root = tmp_path / "telemetry-v3"
    run = telemetry_root / "20260921T120000Z-test"
    run.mkdir(parents=True)
    (run / "ticks.ndjson").write_text('{"tick":1}\n', encoding="utf-8")
    symbiont.write_bytes(b"mind")
    body.write_text("body", encoding="utf-8")

    archived = engine._archive_existing_subject(
        symbiont_file=symbiont,
        body_file=body,
        telemetry_file=telemetry_root,
    )

    assert archived is not None
    assert (archived / symbiont.name).is_file()
    assert (archived / body.name).is_file()
    assert telemetry_root.is_dir()
    assert (run / "ticks.ndjson").is_file()


@pytest.mark.parametrize("failed_artifact", ["symbiont", "body"])
def test_async_checkpoint_failure_is_observable_and_blocks_next_write(
    monkeypatch, tmp_path, failed_artifact
):
    events = []

    def save_bundle(*args):
        events.append("symbiont")
        if failed_artifact == "symbiont":
            raise OSError("disk full")

    def save_body(*args):
        events.append("body")
        if failed_artifact == "body":
            raise OSError("disk full")

    monkeypatch.setattr(engine, "save_symbiont_bundle", save_bundle)
    monkeypatch.setattr(engine, "save_body_state_file", save_body)
    paths = dict(
        symbiont_file=tmp_path / "mind", body_file=tmp_path / "body", models_dir=tmp_path / "models"
    )
    completion = engine._save_checkpoint(_FakeRuntimeForSave(), async_write=True, **paths)
    with pytest.raises(OSError, match="disk full"):
        completion.result(timeout=2)
    before = list(events)
    with pytest.raises(OSError, match="disk full"):
        engine._save_checkpoint(_FakeRuntimeForSave(), active_thread=completion, **paths)
    assert events == before


def test_async_checkpoint_completion_reports_success(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(engine, "save_symbiont_bundle", lambda *args: events.append("mind"))
    monkeypatch.setattr(engine, "save_body_state_file", lambda *args: events.append("body"))
    completion = engine._save_checkpoint(
        _FakeRuntimeForSave(),
        async_write=True,
        symbiont_file=tmp_path / "mind",
        body_file=tmp_path / "body",
        models_dir=tmp_path / "models",
    )
    assert completion.result(timeout=2) is None
    assert events == ["mind", "body"]


@pytest.mark.parametrize("body_tick", [122, None])
def test_resume_requires_matching_body_or_explicit_fresh_body(monkeypatch, tmp_path, body_tick):
    mind, body = tmp_path / "mind", tmp_path / "body"
    mind.write_bytes(b"preserved mind")
    if body_tick is not None:
        body.write_bytes(b"preserved body")
    monkeypatch.setattr(
        engine,
        "load_symbiont_bundle",
        lambda *args: {
            "saved_at_tick": 123,
            "actuation": {"enabled": False},
        },
    )
    monkeypatch.setattr(engine, "load_body_state_file", lambda *args: {"symbiont_ticks": body_tick})

    def unexpected_runtime(**kwargs):
        pytest.fail("must reject implicit reembodiment before creating runtime")

    monkeypatch.setattr(engine, "PyBulletEmbodimentRuntime", unexpected_runtime)
    with pytest.raises(RuntimeError, match="--fresh-body"):
        engine.run(symbiont_file=mind, body_file=body, telemetry_file=tmp_path / "telemetry")
    assert mind.read_bytes() == b"preserved mind"
    if body_tick is not None:
        assert body.read_bytes() == b"preserved body"


@pytest.mark.parametrize("failure_phase", [None, "async", "final"])
def test_run_checkpoint_failure_reaches_caller_after_cleanup(monkeypatch, tmp_path, failure_phase):
    import signal
    from concurrent.futures import Future
    from unittest.mock import Mock

    runtime = Mock()
    runtime.tick_count = 0
    runtime.organism_id = "test"
    runtime.environment_recipe = {}
    runtime.checkpoint.return_value = {}
    runtime.drain_presentation_pose_frames.return_value = []

    def step(**kwargs):
        runtime.tick_count += 1
        return SimpleNamespace(tick=runtime.tick_count, alive=True)

    runtime.step.side_effect = step
    telemetry = Mock(root=tmp_path / "telemetry")
    monkeypatch.setattr(engine, "PyBulletEmbodimentRuntime", lambda **kwargs: runtime)
    monkeypatch.setattr(engine, "AsyncTelemetryV41Writer", lambda *args, **kwargs: telemetry)
    monkeypatch.setattr(engine.ExecutionRates, "observation_due", lambda *args, **kwargs: False)
    writes = []

    def save(*args, async_write=False, **kwargs):
        writes.append("async" if async_write else "final")
        if async_write:
            future = Future()
            if failure_phase == "async":
                future.set_exception(OSError("async failed"))
            else:
                future.set_result(None)
            return future
        if failure_phase == "final":
            raise OSError("final failed")

    monkeypatch.setattr(engine, "_save_checkpoint", save)
    causes = []
    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    kwargs = dict(
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        checkpoint_interval=1,
        symbiont_file=tmp_path / "mind",
        body_file=tmp_path / "body",
        telemetry_file=tmp_path / "telemetry",
        termination_callback=causes.append,
    )
    if failure_phase:
        with pytest.raises(OSError, match=f"{failure_phase} failed"):
            engine.run(**kwargs)
        assert causes == ["error"]
    else:
        assert engine.run(**kwargs) == 0
        assert causes == ["budget_exhausted"]
    assert writes == ["async", "final"]
    runtime.close.assert_called_once()
    telemetry.close.assert_called_once()
    assert {s: signal.getsignal(s) for s in previous} == previous


@pytest.mark.parametrize("fresh_body,body_tick", [(True, 122), (True, None), (False, 123)])
def test_explicit_reembodiment_and_coherent_resume_reach_runtime(
    monkeypatch, tmp_path, fresh_body, body_tick
):
    mind, body = tmp_path / "mind", tmp_path / "body"
    mind.write_bytes(b"mind")
    if body_tick is not None:
        body.write_bytes(b"body")
    checkpoint = {"saved_at_tick": 123, "actuation": {"enabled": False}}
    physical = {"symbiont_ticks": body_tick}
    monkeypatch.setattr(engine, "load_symbiont_bundle", lambda *args: checkpoint)
    monkeypatch.setattr(engine, "load_body_state_file", lambda *args: physical)

    class ReachedRuntime(Exception):
        pass

    def capture_runtime(**kwargs):
        assert kwargs["runtime_checkpoint"] is checkpoint
        assert kwargs["physical_state"] == (None if fresh_body else physical)
        raise ReachedRuntime

    monkeypatch.setattr(engine, "PyBulletEmbodimentRuntime", capture_runtime)
    with pytest.raises(ReachedRuntime):
        engine.run(
            symbiont_file=mind,
            body_file=body,
            fresh_body=fresh_body,
            telemetry_file=tmp_path / "telemetry",
        )
