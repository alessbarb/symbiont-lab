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
