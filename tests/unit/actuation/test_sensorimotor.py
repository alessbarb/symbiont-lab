from __future__ import annotations

import pytest

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


def _teach_repeated_sequence(
    learner: SensorimotorLearner,
    *,
    episodes: int = 2,
) -> None:
    sequence = (
        {"actuator.0": 0.7, "actuator.1": 0.3},
        {"actuator.0": 0.5, "actuator.2": 0.6},
        {"actuator.1": 0.6, "actuator.3": 0.4},
        {"actuator.0": 0.3, "actuator.2": 0.7, "actuator.3": 0.2},
    )
    state = {"sense.a": 0.0, "sense.b": 0.0}
    tick = 0
    for _ in range(episodes):
        for step, vector in enumerate(sequence):
            learner.observe(
                tick=tick,
                body_state=state,
                motor_vector=vector,
                discovery_eligible=True,
            )
            drive = sum(vector.values())
            signed = (step + 1) / len(sequence)
            state = {
                "sense.a": state["sense.a"] + drive * 0.01 * signed,
                "sense.b": state["sense.b"] - drive * 0.006 * signed,
            }
            tick += 1
        # This next pre-action state closes the causal four-action episode.
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
            discovery_eligible=False,
        )
        tick += 1


def test_reproducible_temporal_sequence_can_consolidate_motor_primitive():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-primitive",
        max_concurrent=4,
    )

    _teach_repeated_sequence(learner, episodes=2)

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
    _teach_repeated_sequence(learner, episodes=2)

    primitives = learner.cognitive_primitives
    assert primitives
    primitive = primitives[0]
    intents = learner.primitive_intents(primitive.primitive_id)

    assert intents
    assert {intent.actuator_id for intent in intents} == {
        actuator_id
        for actuator_id, level in primitive.sequence[0]
        if level > 0
    }
    assert len(primitive.sequence) == 4
    assert len(set(primitive.sequence)) > 1
    assert learner.primitive_intents("primitive.not-learned") == ()



def test_candidate_can_be_verified_before_it_is_cognitively_available():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-candidate-verification",
        max_concurrent=4,
    )

    _teach_repeated_sequence(learner, episodes=1)

    assert learner.primitives
    assert learner.cognitive_primitives == ()

    # Find one deterministic replay epoch. Verification may replay the
    # one-episode candidate even though cognition cannot invoke it yet.
    for tick in range(2048):
        intents = learner.motor_intents(tick)
        if learner.last_output_source == "verification":
            assert intents
            assert learner.last_output_primitive_id in {
                primitive.primitive_id for primitive in learner.primitives
            }
            return

    raise AssertionError("expected candidate verification replay")


def test_verification_is_never_rescheduled_twice_in_same_epoch():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-one-verification-per-epoch",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=1)

    first_tick = None
    first_epoch = None
    for tick in range(4096):
        learner.motor_intents(tick)
        if learner.last_output_source == "verification":
            first_tick = tick
            first_epoch = tick // 16
            break

    assert first_tick is not None
    assert first_epoch is not None

    # Finish any remaining ticks of this primitive and inspect the rest of the
    # same epoch. No second verification episode may begin there.
    verification_starts = 1
    was_verifying = True
    for tick in range(first_tick + 1, (first_epoch + 1) * 16):
        learner.motor_intents(tick)
        now_verifying = learner.last_output_source == "verification"
        if now_verifying and not was_verifying:
            verification_starts += 1
        was_verifying = now_verifying

    assert verification_starts == 1



def test_cognitive_primitive_execution_preserves_full_temporal_duration():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-atomic-primitive",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=2)
    primitive = learner.cognitive_primitives[0]

    assert learner.activate_primitive(
        primitive.primitive_id,
        source="cognition",
    )

    outputs = []
    for tick in range(primitive.duration_ticks):
        intents = learner.motor_intents(10_000 + tick)
        outputs.append(
            tuple(
                (intent.actuator_id, round(intent.activation, 6))
                for intent in intents
            )
        )
        assert learner.last_output_source == "primitive"
        assert learner.last_output_primitive_id == primitive.primitive_id

    expected = [
        tuple(
            (actuator_id, round(level / 7.0, 6))
            for actuator_id, level in pattern
            if level > 0
        )
        for pattern in primitive.sequence
    ]
    assert outputs == expected
    assert len(set(outputs)) > 1
    assert learner.active_primitive_id is None



def test_inconsistent_repetition_retracts_false_motor_primitive():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-falsify-primitive",
        max_concurrent=4,
    )
    sequence = (
        {"actuator.0": 0.7, "actuator.1": 0.3},
        {"actuator.0": 0.5, "actuator.2": 0.6},
        {"actuator.1": 0.6, "actuator.3": 0.4},
        {"actuator.0": 0.3, "actuator.2": 0.7},
    )
    state = {"sense.a": 0.0}
    tick = 0

    for sign in (1.0, -1.0):
        for vector in sequence:
            learner.observe(
                tick=tick,
                body_state=state,
                motor_vector=vector,
                discovery_eligible=True,
            )
            state["sense.a"] += sign * sum(vector.values()) * 0.01
            tick += 1
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
            discovery_eligible=False,
        )
        tick += 1

    assert learner.cognitive_primitives == ()



def test_independent_verification_promotes_candidate_to_cognitive_primitive():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-verification-promotes",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=1)

    assert learner.primitives
    assert learner.cognitive_primitives == ()

    state = {"sense.a": 1.0, "sense.b": -0.5}
    started = False
    tick = 100
    primitive_id = None

    while tick < 5000:
        intents = learner.motor_intents(tick)
        if learner.last_output_source == "verification":
            started = True
            primitive_id = learner.last_output_primitive_id
            assert primitive_id is not None
            for step in range(4):
                if step > 0:
                    intents = learner.motor_intents(tick)
                    assert learner.last_output_source == "verification"
                    assert learner.last_output_primitive_id == primitive_id
                vector = {
                    intent.actuator_id: intent.activation
                    for intent in intents
                }
                learner.observe(
                    tick=tick,
                    body_state=state,
                    motor_vector=vector,
                    discovery_eligible=False,
                    execution_primitive_id=primitive_id,
                )
                drive = sum(vector.values())
                state = {
                    "sense.a": state["sense.a"] + drive * 0.01,
                    "sense.b": state["sense.b"] - drive * 0.006,
                }
                tick += 1

            # Close the four-action causal episode with the resulting body state.
            learner.observe(
                tick=tick,
                body_state=state,
                motor_vector={},
                discovery_eligible=False,
                execution_primitive_id=None,
            )
            break
        tick += 1

    assert started
    assert primitive_id is not None
    assert any(
        primitive.primitive_id == primitive_id
        for primitive in learner.cognitive_primitives
    )



def test_babbling_can_discover_temporal_chunk_across_synergy_boundary():
    learner = SensorimotorLearner(
        _ids(8),
        organism_id="org-cross-synergy",
        max_concurrent=4,
    )

    state = {"sense.a": 0.0, "sense.b": 0.0}
    for tick in range(96):
        intents = learner.motor_intents(tick)
        vector = {
            intent.actuator_id: intent.activation
            for intent in intents
        }
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector=vector,
            discovery_eligible=True,
        )
        weighted = sum(
            (index + 1) * value
            for index, (_actuator_id, value)
            in enumerate(sorted(vector.items()))
        )
        state = {
            "sense.a": state["sense.a"] + weighted * 0.002,
            "sense.b": state["sense.b"] - weighted * 0.001,
        }

    # Close the final causal window.
    learner.observe(
        tick=96,
        body_state=state,
        motor_vector={},
        discovery_eligible=False,
    )

    assert learner.primitives
    assert any(
        len(set(primitive.sequence)) > 1
        for primitive in learner.primitives
    )



def test_passive_probe_produces_true_null_motor_output():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-passive-probe",
        max_concurrent=4,
    )

    # First constitutive null probe starts at tick 8.
    outputs = {
        tick: learner.motor_intents(tick)
        for tick in range(13)
    }
    assert any(outputs[tick] for tick in range(1, 8))
    assert outputs[8] == ()
    assert outputs[9] == ()
    assert outputs[10] == ()
    assert outputs[11] == ()
    assert outputs[12]


def test_passive_drift_is_subtracted_from_motor_controllability():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-passive-baseline",
        max_concurrent=4,
    )

    state = {"sense.a": 0.0}
    # Learn one four-tick passive drift baseline of +0.04.
    for tick in range(4):
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
            discovery_eligible=False,
        )
        state["sense.a"] += 0.01
    learner.observe(
        tick=4,
        body_state=state,
        motor_vector={},
        discovery_eligible=False,
    )
    assert learner.snapshot().passive_baseline_samples >= 1

    # Apply a motor sequence while the body changes by exactly the same amount.
    sequence = (
        {"actuator.0": 0.6},
        {"actuator.1": 0.6},
        {"actuator.2": 0.6},
        {"actuator.3": 0.6},
    )
    tick = 6
    for vector in sequence:
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector=vector,
            discovery_eligible=True,
        )
        state["sense.a"] += 0.01
        tick += 1
    learner.observe(
        tick=tick,
        body_state=state,
        motor_vector={},
        discovery_eligible=False,
    )

    assert learner.primitives == ()



@pytest.mark.parametrize(
    "mutator",
    (
        lambda payload: payload.update({"schema_version": True}),
        lambda payload: payload.update({"smoothing": float("nan")}),
        lambda payload: payload["primitives"][0].update({"samples": "2"}),
    ),
)
def test_sensorimotor_restore_rejects_coerced_or_nonfinite_skill_state(mutator):
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-strict-restore",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=2)
    payload = learner.checkpoint()
    assert payload["primitives"]

    mutator(payload)

    with pytest.raises(ValueError):
        SensorimotorLearner.restore(
            payload,
            actuator_ids=_ids(4),
            organism_id="org-strict-restore",
        )



def test_verification_can_be_temporarily_gated_without_stopping_babbling():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-verification-gate",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=1)
    assert learner.primitives

    for tick in range(2048):
        intents = learner.motor_intents(
            tick,
            allow_verification=False,
        )
        assert learner.last_output_source != "verification"
        assert learner.active_primitive_id is None
        # Passive baseline probes are the only legitimate zero-output windows.
        if intents:
            assert learner.last_output_source == "babbling"



def test_unresolved_motor_hypothesis_is_investigated_without_hash_lottery():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-active-investigation",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=1)

    assert learner.hypotheses
    candidate_ids = {item.primitive_id for item in learner.hypotheses}

    # Investigation is evidence-driven, not a sparse random/hash lottery.
    # On the first non-passive opportunity in a fresh epoch the organism
    # actively re-tests one unresolved causal hypothesis.
    intents = learner.motor_intents(100)

    assert intents
    assert learner.last_output_source == "verification"
    assert learner.last_output_primitive_id in candidate_ids
    assert learner.active_investigation_id == learner.last_output_primitive_id


def test_checkpoint_preserves_active_motor_investigation_target():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-investigation-restore",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=1)

    learner.motor_intents(100)
    investigation_id = learner.active_investigation_id
    assert investigation_id is not None

    restored = SensorimotorLearner.restore(
        learner.checkpoint(),
        actuator_ids=_ids(4),
        organism_id="org-investigation-restore",
    )

    assert restored.active_investigation_id == investigation_id
    assert restored.active_primitive_id == learner.active_primitive_id



def test_default_babbling_explores_variable_coordination_cardinality():
    learner = SensorimotorLearner(
        _ids(12),
        organism_id="org-variable-cardinality",
    )

    sizes = {
        len(learner.motor_intents(epoch * 8))
        for epoch in range(64)
        if learner.motor_intents(epoch * 8)
    }

    assert min(sizes) >= 1
    assert max(sizes) <= 12
    assert len(sizes) > 3
    assert max(sizes) > 4


def test_legacy_checkpoint_concurrency_cap_is_not_reintroduced_on_restore():
    learner = SensorimotorLearner(
        _ids(8),
        organism_id="org-legacy-concurrency",
        max_concurrent=4,
    )
    payload = learner.checkpoint()
    payload["schema_version"] = 2
    payload["max_concurrent"] = 4

    restored = SensorimotorLearner.restore(
        payload,
        actuator_ids=_ids(8),
        organism_id="org-legacy-concurrency",
    )

    assert restored._max_concurrent == 8
