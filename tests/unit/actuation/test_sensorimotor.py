from __future__ import annotations

from symbiont.actuation.sensorimotor import SensorimotorLearner


def _ids(count: int = 8) -> tuple[str, ...]:
    return tuple(f"actuator.{index}" for index in range(count))


def test_babbling_covers_all_actuators_without_single_channel_monopoly():
    learner = SensorimotorLearner(
        _ids(),
        organism_id="org-babble",
        max_concurrent=4,
    )

    seen = set()
    for tick in range(128):
        intents = learner.motor_intents(tick)
        assert len(intents) <= 4
        seen.update(intent.actuator_id for intent in intents)

    assert seen == set(_ids())
    assert learner.babbling_coverage == 1.0


def test_babbling_holds_channel_set_within_short_epoch():
    learner = SensorimotorLearner(
        _ids(),
        organism_id="org-hold",
        max_concurrent=4,
    )

    sets = []
    for tick in range(1, 7):
        intents = learner.motor_intents(tick)
        sets.append({intent.actuator_id for intent in intents})

    assert sets
    assert all(current == sets[0] for current in sets[1:])


def test_multi_horizon_statistics_are_recorded_independently():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-horizons",
        max_concurrent=4,
    )

    state = {f"sense.{i}": 0.0 for i in range(4)}
    previous_vector = {}
    for tick in range(90):
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector=previous_vector,
        )
        intents = learner.motor_intents(tick)
        previous_vector = {
            intent.actuator_id: intent.activation for intent in intents
        }
        # Deterministic body response to the current pattern.
        drive = sum(previous_vector.values()) / max(1, len(previous_vector))
        state = {
            key: value + drive * (0.001 + index * 0.0001)
            for index, (key, value) in enumerate(state.items())
        }

    snapshot = learner.snapshot()
    counts = dict(snapshot.horizon_samples)
    assert counts[1] > 0
    assert counts[4] > 0
    assert counts[16] > 0
    assert counts[64] > 0
    assert snapshot.known_patterns > 0


def _teach_repeated_pattern(
    learner: SensorimotorLearner,
    *,
    episodes: int = 2,
) -> None:
    pattern = {
        "actuator.0": 0.7,
        "actuator.1": 0.5,
        "actuator.2": 0.4,
    }
    state = {"sense.a": 0.0, "sense.b": 0.0}
    tick = 0
    for _ in range(episodes):
        for _step in range(4):
            learner.observe(
                tick=tick,
                body_state=state,
                motor_vector=pattern,
            )
            drive = sum(pattern.values())
            state = {
                "sense.a": state["sense.a"] + drive * 0.01,
                "sense.b": state["sense.b"] + drive * 0.007,
            }
            tick += 1
        # Empty frame ends the episode so the next occurrence counts as an
        # independent sustained sample rather than continuation of one hold.
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
        )
        tick += 1


def test_reproducible_sustained_pattern_can_consolidate_motor_primitive():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-primitive",
        max_concurrent=4,
    )

    _teach_repeated_pattern(learner, episodes=2)

    snapshot = learner.snapshot()
    assert snapshot.primitives > 0
    assert snapshot.best_controllability > 0.0
    assert learner.primitives
    assert learner.cognitive_primitives


def test_sensorimotor_checkpoint_roundtrip_preserves_learning_state():
    learner = SensorimotorLearner(
        _ids(6),
        organism_id="org-restore",
        max_concurrent=4,
    )

    state = {"sense.a": 0.0}
    previous_vector = {}
    for tick in range(100):
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector=previous_vector,
        )
        intents = learner.motor_intents(tick)
        previous_vector = {
            intent.actuator_id: intent.activation for intent in intents
        }
        state["sense.a"] += sum(previous_vector.values()) * 0.001

    restored = SensorimotorLearner.restore(
        learner.checkpoint(),
        actuator_ids=_ids(6),
        organism_id="org-restore",
    )

    assert restored.snapshot() == learner.snapshot()
    assert restored.primitives == learner.primitives


def test_cognitive_primitive_replays_only_learned_motor_pattern():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-cognitive-primitive",
        max_concurrent=4,
    )
    _teach_repeated_pattern(learner, episodes=2)

    primitives = learner.cognitive_primitives
    assert primitives
    primitive = primitives[0]
    intents = learner.primitive_intents(primitive.primitive_id)

    assert intents
    assert {intent.actuator_id for intent in intents} == {
        actuator_id for actuator_id, level in primitive.pattern if level > 0
    }
    assert learner.primitive_intents("primitive.not-learned") == ()
