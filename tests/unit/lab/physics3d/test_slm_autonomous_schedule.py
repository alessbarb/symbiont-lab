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
    manager._last_internal_validation_loss = None
    manager._last_internal_validation_accuracy = None
    manager._last_epochs_completed = None
    manager._last_steps_completed = None
    manager._last_parameter_count = None
    manager._last_resolved_embedding_dim = None
    manager._last_resolved_hidden_dim = None
    manager._last_vocab_size = None
    return manager


def test_slm_manager_does_not_invent_training_without_organism_plan(tmp_path):
    manager = _manager(tmp_path)
    runtime = _FakeRuntime(None)

    assert manager.maybe_schedule(runtime, current_tick=100) is False
    assert runtime.calls == 1
    assert manager._executor.calls == []


def test_slm_manager_only_services_organism_authored_plan(tmp_path):
    plan = SimpleNamespace(
        request=SimpleNamespace(
            requested_epochs=6,
            requested_steps=39,
        ),
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
    assert manager.last_plan_epochs == 6
    assert manager.last_plan_steps == 39


class _FakeFuture:
    def __init__(self, *, done: bool, cancel_result: bool = False) -> None:
        self._done = done
        self._cancel_result = cancel_result
        self.cancel_calls = 0

    def done(self) -> bool:
        return self._done

    def cancel(self) -> bool:
        self.cancel_calls += 1
        return self._cancel_result


class _ClosingExecutor:
    def __init__(self) -> None:
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


def test_slm_close_uses_normal_shutdown_when_worker_is_idle(tmp_path):
    manager = _manager(tmp_path)
    executor = _ClosingExecutor()
    manager._executor = executor
    manager._future = None

    manager.close()

    assert executor.shutdown_calls == [(False, True)]


def test_slm_close_uses_normal_shutdown_when_pending_future_cancels(tmp_path):
    manager = _manager(tmp_path)
    executor = _ClosingExecutor()
    future = _FakeFuture(done=False, cancel_result=True)
    manager._executor = executor
    manager._future = future

    manager.close()

    assert future.cancel_calls == 1
    assert executor.shutdown_calls == [(False, True)]


def test_slm_close_delegates_running_worker_to_force_stop(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    executor = _ClosingExecutor()
    future = _FakeFuture(done=False, cancel_result=False)
    manager._executor = executor
    manager._future = future
    seen = []

    monkeypatch.setattr(
        manager,
        "_force_stop_executor",
        lambda supplied: seen.append(supplied),
    )

    manager.close()

    assert future.cancel_calls == 1
    assert seen == [executor]
    assert executor.shutdown_calls == []
