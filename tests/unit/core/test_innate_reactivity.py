from __future__ import annotations

from symbiont.core.regulation import (
    ActionArbitrator,
    InnateReactivity,
    ReactiveMemory,
    ReactiveState,
)


def test_innate_reactivity_detects_worsening_without_anatomy() -> None:
    system = InnateReactivity(acute_velocity=0.02, smoothing=1.0)
    first = system.evaluate(
        percepts={"signal.a": 0.2, "signal.b": 0.4},
        homeostatic_deviation=0.10,
    )
    second = system.evaluate(
        percepts={"signal.a": 0.2, "signal.b": 0.4},
        homeostatic_deviation=0.20,
    )
    assert first.withdrawal == 0.0
    assert second.withdrawal == 1.0
    assert second.interrupt == 1.0


def test_innate_reactivity_orients_to_opaque_unexpected_change() -> None:
    system = InnateReactivity(surprise_threshold=0.10, smoothing=1.0)
    system.evaluate(percepts={"opaque.7": 0.1}, homeostatic_deviation=0.1)
    state = system.evaluate(
        percepts={"opaque.7": 0.9},
        homeostatic_deviation=0.1,
    )
    assert state.surprise > 0.7
    assert state.interrupt > 0.7
    assert state.withdrawal == 0.0


def test_reactive_memory_requires_repeated_real_relief() -> None:
    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    assert memory.best(
        signature="r3:s0:c0",
        candidates=("primitive.x",),
    ) is None
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    assert memory.best(
        signature="r3:s0:c0",
        candidates=("primitive.x",),
    ) == "primitive.x"


def test_negative_experience_prevents_fast_response() -> None:
    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=-0.2)
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=-0.1)
    assert memory.best(
        signature="r3:s0:c0",
        candidates=("primitive.x",),
    ) is None


def test_arbitrator_never_invents_motor_action() -> None:
    memory = ReactiveMemory()
    state = ReactiveState(
        interrupt=1.0,
        withdrawal=1.0,
        stabilization=0.8,
        conservation=0.5,
        attention=1.0,
        deviation=0.7,
        deviation_velocity=0.2,
        surprise=0.8,
        signature="r3:s3:c1",
    )
    decision = ActionArbitrator().choose_reactive(
        state=state,
        memory=memory,
        candidate_ids=("primitive.a", "primitive.b"),
    )
    assert decision.primitive_id is None
    assert decision.reason == "acute_no_learned_response"


def test_reactive_checkpoint_roundtrip() -> None:
    system = InnateReactivity(smoothing=1.0)
    system.evaluate(percepts={"opaque.1": 0.2}, homeostatic_deviation=0.1)
    restored = InnateReactivity.restore(system.checkpoint())
    state = restored.evaluate(
        percepts={"opaque.1": 0.8},
        homeostatic_deviation=0.2,
    )
    assert state.interrupt > 0.0

    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    restored_memory = ReactiveMemory.restore(memory.checkpoint())
    assert restored_memory.best(
        signature="r3:s0:c0",
        candidates=("primitive.x",),
    ) == "primitive.x"
