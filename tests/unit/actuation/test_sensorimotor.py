from __future__ import annotations

import hashlib

import pytest

from symbiont.actuation.sensorimotor import MotorPrimitive, SensorimotorLearner


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
    for episode_index in range(episodes):
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
        # Independent recurrence must come from a later babbling block. Pad
        # only between episodes; padding after the final episode would clear
        # last_natural_competence_ids, which is intentionally one-tick evidence.
        if episode_index + 1 < episodes:
            while tick % 8:
                learner.observe(
                    tick=tick,
                    body_state=state,
                    motor_vector={},
                    discovery_eligible=False,
                )
                tick += 1


def test_single_episode_remains_candidate_until_independent_recurrence():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-single-episode-candidate",
        max_concurrent=4,
    )
    sequence = (
        (("actuator.0", 5), ("actuator.1", 3)),
        (("actuator.0", 4), ("actuator.2", 4)),
        (("actuator.1", 5), ("actuator.3", 2)),
        (("actuator.0", 3), ("actuator.2", 5)),
    )

    result = learner._record_primitive_episode(
        sequence=sequence,
        before={"sense.x": 0.0},
        after={"sense.x": 0.1},
        end_tick=4,
        may_create=True,
    )

    assert result is None
    assert learner.primitives == ()
    snapshot = learner.snapshot()
    assert snapshot.primitive_candidates == 1
    assert snapshot.recurrent_primitive_candidates == 0
    lifecycle = learner.checkpoint()["primitive_stats"][0]
    assert lifecycle["first_sample_tick"] == 4
    assert lifecycle["last_sample_tick"] == 4
    assert lifecycle["materialized_tick"] is None
    assert lifecycle["competence_tick"] is None


def test_adjacent_windows_from_same_babbling_block_do_not_count_as_recurrence():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-same-evidence-block",
        max_concurrent=4,
    )
    sequence = (
        (("actuator.0", 5),),
        (("actuator.1", 5),),
        (("actuator.2", 5),),
        (("actuator.3", 5),),
    )

    learner._record_primitive_episode(
        sequence=sequence,
        before={"sense.x": 0.0},
        after={"sense.x": 0.1},
        end_tick=4,
        may_create=True,
        evidence_blocks=frozenset({0}),
    )
    learner._record_primitive_episode(
        sequence=sequence,
        before={"sense.x": 0.0},
        after={"sense.x": 0.1},
        end_tick=8,
        may_create=True,
        evidence_blocks=frozenset({0}),
    )

    assert learner.snapshot().recurrent_primitive_candidates == 0
    assert learner.primitives == ()


def test_same_sequence_in_disjoint_babbling_block_counts_as_recurrence():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-independent-evidence-block",
        max_concurrent=4,
    )
    sequence = (
        (("actuator.0", 5),),
        (("actuator.1", 5),),
        (("actuator.2", 5),),
        (("actuator.3", 5),),
    )

    learner._record_primitive_episode(
        sequence=sequence,
        before={"sense.x": 0.0},
        after={"sense.x": 0.1},
        end_tick=4,
        may_create=True,
        evidence_blocks=frozenset({0}),
    )
    learner._record_primitive_episode(
        sequence=sequence,
        before={"sense.x": 0.0},
        after={"sense.x": 0.1},
        end_tick=12,
        may_create=True,
        evidence_blocks=frozenset({1}),
    )

    assert learner.primitives
    assert learner.primitives[0].samples == 2


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
    lifecycle_items = learner.checkpoint()["primitive_stats"]
    promoted = [
        item for item in lifecycle_items
        if item["materialized_tick"] is not None
    ]
    assert promoted
    assert all(item["first_sample_tick"] <= item["materialized_tick"] for item in promoted)
    competent = [item for item in promoted if item["competence_tick"] is not None]
    assert competent
    assert all(item["materialized_tick"] <= item["competence_tick"] for item in competent)


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



def test_cognitive_primitive_execution_preserves_full_temporal_duration():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-atomic-primitive",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=2)
    primitive = learner.cognitive_primitives[0]

    assert learner.activate_primitive(primitive.primitive_id)

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

    checkpoint = learner.checkpoint()
    assert checkpoint["primitive_stats"]
    assert any(
        len({
            tuple((item[0], item[1]) for item in pattern)
            for pattern in candidate["sequence"]
        }) > 1
        for candidate in checkpoint["primitive_stats"]
    )



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
        lambda payload: payload["primitives"][0].update(
            {"samples": payload["primitives"][0]["samples"] + 1}
        ),
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


@pytest.mark.parametrize(
    "lifecycle_mutator",
    (
        lambda item: item.pop("first_sample_tick"),
        lambda item: item.update({"last_sample_tick": item["first_sample_tick"] - 1}),
        lambda item: item.update({"competence_tick": 1, "materialized_tick": None}),
    ),
)
def test_sensorimotor_restore_rejects_corrupted_primitive_lifecycle(lifecycle_mutator):
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-lifecycle-restore",
        max_concurrent=4,
    )
    _teach_repeated_sequence(learner, episodes=2)
    payload = learner.checkpoint()
    lifecycle_mutator(payload["primitive_stats"][0])

    with pytest.raises(ValueError):
        SensorimotorLearner.restore(
            payload,
            actuator_ids=_ids(4),
            organism_id="org-lifecycle-restore",
        )


@pytest.mark.parametrize("legacy_schema", [1, 2, 3, 4, 5, 6])
def test_restore_rejects_every_pre_v7_schema_outright(legacy_schema):
    """Older checkpoints cannot be represented honestly by the v7 learner.

    Pre-L6 state may carry removed verification apparatus; v5 contains motor
    evidence gathered under uniform 1..N babbling, and v6 lacks provenance
    needed to distinguish independent recurrence from temporal self-overlap.
    """
    learner = SensorimotorLearner(_ids(4), organism_id="org-legacy-schema")
    payload = learner.checkpoint()
    payload["schema_version"] = legacy_schema

    with pytest.raises(ValueError):
        SensorimotorLearner.restore(
            payload,
            actuator_ids=_ids(4),
            organism_id="org-legacy-schema",
        )


def test_restore_rejects_in_flight_verification_replay_instead_of_relabeling_it():
    """An action the removed scheduler forced must never resurface as
    cognition-originated after restore — that would rewrite the organism's
    own causal history (not merely legacy debt)."""
    learner = SensorimotorLearner(_ids(4), organism_id="org-verification-reject")
    _teach_repeated_sequence(learner, episodes=2)
    primitive = learner.cognitive_primitives[0]
    assert learner.activate_primitive(primitive.primitive_id)

    payload = learner.checkpoint()
    assert payload["replay_id"] == primitive.primitive_id
    payload["replay_source"] = "verification"

    with pytest.raises(ValueError):
        SensorimotorLearner.restore(
            payload,
            actuator_ids=_ids(4),
            organism_id="org-verification-reject",
        )


def test_restore_rejects_in_flight_replay_with_missing_or_unknown_source():
    learner = SensorimotorLearner(_ids(4), organism_id="org-missing-source")
    _teach_repeated_sequence(learner, episodes=2)
    primitive = learner.cognitive_primitives[0]
    assert learner.activate_primitive(primitive.primitive_id)

    payload = learner.checkpoint()
    del payload["replay_source"]

    with pytest.raises(ValueError):
        SensorimotorLearner.restore(
            payload,
            actuator_ids=_ids(4),
            organism_id="org-missing-source",
        )


def test_default_babbling_prefers_low_dimensional_coordination_without_forbidding_broad_patterns():
    learner = SensorimotorLearner(
        _ids(62),
        organism_id="org-variable-cardinality",
    )

    sizes = [
        learner._babble_cardinality(epoch)
        for epoch in range(512)
    ]

    assert min(sizes) >= 1
    assert max(sizes) <= 62
    assert len(set(sizes)) > 8
    ordered = sorted(sizes)
    median = ordered[len(ordered) // 2]
    assert median <= 10
    assert sum(size <= 10 for size in sizes) > len(sizes) / 2
    assert any(size > 31 for size in sizes)


def test_cognitive_primitives_are_not_arbitrarily_truncated_to_eight():
    learner = SensorimotorLearner(
        _ids(12),
        organism_id="org-many-competences",
    )

    from symbiont.actuation.sensorimotor import MotorPrimitive

    for index in range(12):
        actuator_id = f"actuator.{index}"
        sequence = tuple(
            ((actuator_id, 5),)
            for _ in range(4)
        )
        primitive = MotorPrimitive(
            primitive_id=f"primitive.test.{index}",
            sequence=sequence,
            samples=3,
            effect_mean=0.1,
            effect_variance=0.0,
            controllability=0.1 + index * 0.001,
            directional_consistency=1.0,
        )
        learner._primitives[primitive.primitive_id] = primitive

    assert len(learner.cognitive_primitives) == 12



def test_noncontiguous_temporal_window_is_ignored_without_error():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-noncontiguous-window",
        max_concurrent=4,
    )
    state = {"sense.a": 0.0}

    for tick in range(4):
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
            discovery_eligible=False,
        )
        state["sense.a"] += 0.01

    # Skip tick 4 deliberately. The incomplete temporal window must be ignored,
    # not interpreted as passive/motor evidence and not raise.
    learner.observe(
        tick=5,
        body_state=state,
        motor_vector={},
        discovery_eligible=False,
    )

    assert learner.snapshot().passive_baseline_samples == 0



def test_primitive_ordered_views_are_cached_and_invalidated_on_update():
    learner = SensorimotorLearner(
        ("a", "b"),
        organism_id="cache-test",
    )
    first = MotorPrimitive(
        primitive_id="primitive.b",
        sequence=((("a", 1),),) * 4,
        samples=2,
        effect_mean=0.1,
        effect_variance=0.0,
        controllability=0.1,
        directional_consistency=1.0,
    )
    second = MotorPrimitive(
        primitive_id="primitive.a",
        sequence=((("b", 1),),) * 4,
        samples=2,
        effect_mean=0.1,
        effect_variance=0.0,
        controllability=0.2,
        directional_consistency=1.0,
    )
    learner._primitives[first.primitive_id] = first
    learner._primitives[second.primitive_id] = second
    learner._invalidate_primitive_caches()

    ordered_a = learner.primitives
    ordered_b = learner.primitives
    cognitive_a = learner.cognitive_primitives
    cognitive_b = learner.cognitive_primitives

    assert ordered_a is ordered_b
    assert cognitive_a is cognitive_b
    assert [item.primitive_id for item in ordered_a] == ["primitive.a", "primitive.b"]

    replacement = MotorPrimitive(
        primitive_id="primitive.a",
        sequence=second.sequence,
        samples=3,
        effect_mean=0.2,
        effect_variance=0.0,
        controllability=0.3,
        directional_consistency=1.0,
    )
    learner._primitives[replacement.primitive_id] = replacement
    learner._invalidate_primitive_caches()

    assert learner.primitives is not ordered_a
    assert learner.cognitive_primitives is not cognitive_a
    assert learner.primitives[0] is replacement



def test_observe_precomputes_the_exact_canonical_motor_pattern():
    learner = SensorimotorLearner(("b", "a"), organism_id="frame-pattern")
    vector = {"b": 0.51, "a": 0.09}
    learner.observe(tick=1, body_state={"x": 0.0}, motor_vector=vector)

    frame = learner._frames[-1]
    assert frame.motor_pattern == (
        ("a", round(0.09 * 7)),
        ("b", round(0.51 * 7)),
    )


def test_primitive_id_cache_preserves_sha256_identity_and_reuses_result():
    learner = SensorimotorLearner(("a",), organism_id="primitive-id-cache")
    sequence = (
        (("a", 1),),
        (("a", 2),),
        (("a", 3),),
        (("a", 4),),
    )
    expected = "primitive." + hashlib.sha256(
        repr(sequence).encode("utf-8")
    ).hexdigest()[:16]

    first = learner._primitive_id_for_sequence(sequence)
    second = learner._primitive_id_for_sequence(sequence)

    assert first == expected
    assert second == expected
    assert learner._primitive_id_by_sequence == {sequence: expected}


def test_natural_recurrence_surfaces_competence_without_forced_replay():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-natural-competence",
        max_concurrent=4,
    )

    _teach_repeated_sequence(learner, episodes=2)

    assert learner.cognitive_primitives
    assert learner.last_natural_competence_ids
    assert set(learner.last_natural_competence_ids).issubset(
        {primitive.primitive_id for primitive in learner.cognitive_primitives}
    )
    assert learner.active_primitive_id is None


def test_similar_natural_chunks_count_as_recurrence_not_new_skill():
    learner = SensorimotorLearner(
        ("a", "b"),
        organism_id="approx-recurrence",
    )
    first = (
        (("a", 4), ("b", 2)),
        (("a", 5), ("b", 2)),
        (("a", 5), ("b", 3)),
        (("a", 4), ("b", 3)),
    )
    second = (
        (("a", 4), ("b", 2)),
        (("a", 4), ("b", 2)),
        (("a", 5), ("b", 3)),
        (("a", 4), ("b", 3)),
    )

    learner._record_primitive_episode(
        sequence=first,
        before={"sense.x": 0.0},
        after={"sense.x": 0.05},
        end_tick=4,
        may_create=True,
        evidence_blocks=frozenset({0}),
    )
    learner._record_primitive_episode(
        sequence=second,
        before={"sense.x": 0.0},
        after={"sense.x": 0.05},
        end_tick=12,
        may_create=True,
        evidence_blocks=frozenset({1}),
    )

    assert len(learner.primitives) == 1
    primitive = learner.primitives[0]
    assert primitive.samples == 2
    assert primitive.is_competence


def test_bounded_primitive_pool_preserves_proven_competence():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-retain-competence",
        max_concurrent=4,
    )

    sequence = (
        (("actuator.0", 4),),
        (("actuator.1", 4),),
        (("actuator.2", 4),),
        (("actuator.3", 4),),
    )

    competence = MotorPrimitive(
        primitive_id="primitive.competence",
        sequence=sequence,
        samples=2,
        effect_mean=0.01,
        effect_variance=0.001,
        controllability=0.01,
        directional_consistency=0.8,
    )
    assert competence.is_competence

    learner._primitives = {
        f"primitive.unverified.{index:02d}": MotorPrimitive(
            primitive_id=f"primitive.unverified.{index:02d}",
            sequence=sequence,
            samples=1,
            effect_mean=1.0,
            effect_variance=0.0,
            controllability=1.0 - index * 0.001,
            directional_consistency=1.0,
        )
        for index in range(32)
    }
    learner._primitives[competence.primitive_id] = competence

    learner._enforce_primitive_bound()

    assert len(learner.primitives) == 32
    assert competence.primitive_id in {
        primitive.primitive_id for primitive in learner.primitives
    }
    assert competence.primitive_id in learner.available_cognitive_primitive_ids()



def test_primitive_episode_provenance_is_ephemeral_and_independent():
    learner = SensorimotorLearner(
        _ids(4),
        organism_id="org-episode-provenance",
        max_concurrent=4,
    )

    _teach_repeated_sequence(learner, episodes=2)

    assert learner.last_primitive_episodes
    episode = learner.last_primitive_episodes[-1]
    assert episode.end_tick - episode.start_tick == 4
    assert episode.sample_index >= 2
    assert len(episode.evidence_blocks) >= 1
    assert episode.source == "natural"

    checkpoint = learner.checkpoint()
    assert "episodes" not in checkpoint

    learner.observe(
        tick=episode.end_tick + 1,
        body_state={"sense.a": 1.0, "sense.b": -1.0},
        motor_vector={},
        discovery_eligible=False,
    )
    assert learner.last_primitive_episodes == ()
