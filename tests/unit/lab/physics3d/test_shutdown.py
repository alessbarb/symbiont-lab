from __future__ import annotations

from types import SimpleNamespace

import pytest

from symbiont_lab.physics3d import cli
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

    def checkpoint(self):
        return {"saved_at_tick": self.tick_count, "organism_id": "test"}

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

    monkeypatch.setattr(cli, "save_symbiont_bundle", save_bundle)
    monkeypatch.setattr(cli, "save_body_state_file", save_body)

    runtime = _FakeRuntimeForSave(
        physical_error=RuntimeError("physics server already closed")
    )

    with pytest.raises(RuntimeError, match="physics server already closed"):
        cli._save_checkpoint(
            runtime,
            symbiont_file=tmp_path / "subject.symbiont",
            body_file=tmp_path / "body.json",
            models_dir=tmp_path / "models",
        )

    assert events == ["symbiont"]


def test_checkpoint_writes_body_with_its_own_completed_tick(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "save_symbiont_bundle",
        lambda payload, models_dir, path: path,
    )

    def save_body(payload, path):
        captured.update(payload)
        return path

    monkeypatch.setattr(cli, "save_body_state_file", save_body)

    runtime = _FakeRuntimeForSave(tick=321)
    cli._save_checkpoint(
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

    archived = cli._archive_existing_subject(
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


def test_new_subject_preserves_v3_telemetry_history(tmp_path):
    symbiont = tmp_path / "subject.symbiont"
    body = tmp_path / "subject.body-v4.json"
    telemetry_root = tmp_path / "telemetry-v3"
    run = telemetry_root / "20260921T120000Z-test"
    run.mkdir(parents=True)
    (run / "ticks.ndjson").write_text('{"tick":1}\n', encoding="utf-8")
    symbiont.write_bytes(b"mind")
    body.write_text("body", encoding="utf-8")

    archived = cli._archive_existing_subject(
        symbiont_file=symbiont,
        body_file=body,
        telemetry_file=telemetry_root,
    )

    assert archived is not None
    assert (archived / symbiont.name).is_file()
    assert (archived / body.name).is_file()
    assert telemetry_root.is_dir()
    assert (run / "ticks.ndjson").is_file()
