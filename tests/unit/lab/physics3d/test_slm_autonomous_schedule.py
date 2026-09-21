from __future__ import annotations

from types import SimpleNamespace

from symbiont_lab.physics3d.slm import Physics3DSlmManager


class _FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def submit(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(done=lambda: False)


class _FakeRuntime:
    def __init__(self, plan) -> None:
        self._plan = plan
        self.calls = 0

    def autonomous_private_learning_plan(self):
        self.calls += 1
        return self._plan


def _manager(tmp_path) -> Physics3DSlmManager:
    manager = object.__new__(Physics3DSlmManager)
    manager.models_dir = tmp_path
    manager.train_interval = 1
    manager.device = "cpu"
    manager._executor = _FakeExecutor()
    manager._future = None
    manager._last_submitted_tick = -1
    manager._last_error = None
    manager._last_gate_reason = None
    manager._last_gate_gain = None
    manager._last_candidate_loss = None
    manager._last_best_baseline = None
    manager._last_best_baseline_loss = None
    manager._last_plan_reason = None
    manager._last_plan_replay_pressure = None
    manager._last_plan_epochs = None
    manager._last_plan_steps = None
    return manager


def test_slm_manager_does_not_invent_training_without_organism_plan(tmp_path):
    manager = _manager(tmp_path)
    runtime = _FakeRuntime(None)

    assert manager.maybe_schedule(runtime, current_tick=100) is False
    assert runtime.calls == 1
    assert manager._executor.calls == []


def test_slm_manager_only_services_organism_authored_plan(tmp_path):
    plan = SimpleNamespace(
        request=object(),
        corpus=object(),
        tokenizer=SimpleNamespace(vocabulary=("a", "b")),
        reason="prediction-revision",
        transition_count=96,
        replay_pressure=0.75,
    )
    manager = _manager(tmp_path)
    runtime = _FakeRuntime(plan)

    assert manager.maybe_schedule(runtime, current_tick=100) is True
    assert runtime.calls == 1
    assert len(manager._executor.calls) == 1
    assert manager.last_plan_reason == "prediction-revision"
    assert manager.last_plan_replay_pressure == 0.75
