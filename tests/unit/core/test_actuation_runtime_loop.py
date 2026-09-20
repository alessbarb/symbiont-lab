from __future__ import annotations

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.runtime import OrganismRuntime


def _runtime() -> OrganismRuntime:
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    return OrganismRuntime(
        organism_id="motor-runtime",
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        bootstrap_semantic_senses=False,
        discover_senses=False,
        min_samples=1,
    )


def test_proprioception_from_actuation_enters_sensory_pipeline_on_following_tick():
    runtime = _runtime()
    actuation_tick = None
    for _ in range(32):
        result = runtime.tick()
        if result.actuation is not None:
            actuation_tick = result.tick
            break
    assert actuation_tick is not None

    following = runtime.tick()
    motor_sensors = [
        sensor
        for sensor in runtime.sensory_system.sensors
        if any(source_id.startswith("motor.") for source_id in sensor.source_ids)
    ]
    assert motor_sensors
    assert following.tick == actuation_tick + 1
    assert any(
        percept.sensor_id in {sensor.sensor_id for sensor in motor_sensors}
        for percept in following.percepts
    )


def test_proprioceptive_echo_alone_cannot_promote_an_actuator_as_world_causal():
    runtime = _runtime()
    # No host/world source is attached. Motor proprioception will still be
    # produced after ON probes, but controllability explicitly excludes those
    # echo channels. Therefore no external effect relation can be learned.
    runtime.run(160)
    proposer = runtime._actuator_proposer
    assert proposer is not None
    assert proposer.active_repertoire == ()
    assert all(not state.effect_relations for state in proposer.states)



def test_checkpoint_never_persists_raw_pending_motor_percept_baseline():
    runtime = _runtime()
    for _ in range(32):
        runtime.tick()
        if runtime._pending_motor_observation:
            break
    assert runtime._pending_motor_observation

    payload = runtime.checkpoint()
    pending = payload["actuation"]["pending_motor_observation"]
    assert isinstance(pending, list)
    assert pending
    assert all("baseline" not in item for item in pending)

    restored = runtime.from_checkpoint(
        payload,
        min_samples=1,
        bootstrap_semantic_senses=False,
        discover_senses=False,
        kernel_limits=KernelLimits(),
    )
    restored_pending = restored._pending_motor_observation
    assert restored_pending
    assert restored_pending[0][2] is None

    # The physical probing phase still advances on the next tick; only the
    # incomplete t->t+1 evidence sample is deliberately cold-started.
    actuator_id = restored_pending[0][0]
    before = next(
        state.tick_in_window
        for state in restored._actuator_proposer.states
        if state.actuator_id == actuator_id
    )
    restored.tick()
    after = next(
        state.tick_in_window
        for state in restored._actuator_proposer.states
        if state.actuator_id == actuator_id
    )
    assert after != before or after == 0



def test_runtime_can_execute_multiple_cognitive_motor_intents_concurrently():
    runtime = _runtime()
    proposer = runtime._actuator_proposer
    assert proposer is not None

    # Promote four slots directly for this unit-level concurrency contract.
    active_ids = runtime.actuator_constitution.actuator_ids[:4]
    for state in proposer.states:
        if state.actuator_id in active_ids:
            state.probing_state = "active"

    class FakeCognition:
        def readouts_for_family(self, family):
            assert family == "motor"
            return {
                active_ids[0]: 0.9,
                active_ids[1]: 0.8,
                active_ids[2]: 0.7,
                active_ids[3]: 0.6,
            }

    runtime._motor_step(FakeCognition(), (), tick=1)

    assert len(runtime.last_motor_intents) == 4
    assert len(runtime.last_actuations) == 4
    assert {item.actuator_id for item in runtime.last_actuations} == set(active_ids)
    assert runtime.last_motor_origin == "cognition"



def test_babbling_sensorimotor_state_survives_runtime_checkpoint_roundtrip():
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    runtime = OrganismRuntime(
        organism_id="motor-babbling-runtime",
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        motor_exploration_mode="babbling",
        bootstrap_semantic_senses=False,
        discover_senses=False,
        min_samples=1,
    )

    for _ in range(24):
        runtime.tick()

    before = runtime.sensorimotor_snapshot
    assert before is not None
    assert before.babbling_coverage > 0.0

    payload = runtime.checkpoint()
    assert payload["actuation"]["exploration_mode"] == "babbling"
    assert isinstance(payload["actuation"]["sensorimotor"], dict)

    restored = OrganismRuntime.from_checkpoint(
        payload,
        min_samples=1,
        bootstrap_semantic_senses=False,
        discover_senses=False,
        kernel_limits=limits,
    )
    after = restored.sensorimotor_snapshot

    assert after is not None
    assert after == before



def test_pending_primitive_verification_context_survives_checkpoint_roundtrip():
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    runtime = OrganismRuntime(
        organism_id="motor-primitive-context-runtime",
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        motor_exploration_mode="babbling",
        bootstrap_semantic_senses=False,
        discover_senses=False,
        min_samples=1,
    )
    runtime._pending_primitive_choice_context = (
        "primitive.test",
        ("concept.a", "concept.b"),
        123,
    )

    payload = runtime.checkpoint()
    pending = payload["actuation"]["pending_primitive_choice_context"]
    assert pending == {
        "primitive_id": "primitive.test",
        "concept_ids": ["concept.a", "concept.b"],
        "complete_tick": 123,
    }

    restored = OrganismRuntime.from_checkpoint(
        payload,
        min_samples=1,
        bootstrap_semantic_senses=False,
        discover_senses=False,
        kernel_limits=limits,
    )

    assert restored._pending_primitive_choice_context == (
        "primitive.test",
        ("concept.a", "concept.b"),
        123,
    )
