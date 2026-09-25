from __future__ import annotations

import pytest

from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.physiology import LivingBodyState


def _runtime() -> OrganismRuntime:
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    body_state = LivingBodyState(
        energy_reserve=100.0,
        max_energy=100.0,
    )
    return OrganismRuntime(
        organism_id="motor-runtime",
        living_body_state=body_state,
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        actuator_constitution=derive_actuator_constitution(8, physical_contract="unit-motor-runtime-v2"),
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
    proposer = runtime.actuator_evidence_model
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

    # Only the incomplete t->t+1 evidence sample is deliberately cold-
    # started; the restored organism must still tick without error.
    restored.tick()



def test_cognitive_motor_readouts_cannot_bypass_competence_layer():
    runtime = _runtime()
    actuator_id = runtime.actuator_constitution.actuator_ids[0]

    class FakeCognition:
        def readouts_for_family(self, family):
            if family == "motor":
                return {actuator_id: 1.0}
            if family == "primitive":
                return {}
            return {}

    runtime._motor_step(FakeCognition(), (), tick=1)

    assert runtime.last_action_source != "competence"
    assert runtime._active_action_commitment is not None
    assert runtime._active_action_commitment.competence_id is None


def test_motor_command_is_traced_to_active_commitment_before_actuation():
    runtime = _runtime()
    runtime._motor_step(None, (), tick=1)

    if runtime.last_motor_intents:
        assert runtime._active_action_commitment is not None
        assert runtime._last_motor_command is not None
        assert (
            runtime._last_motor_command.commitment_id
            == runtime._active_action_commitment.commitment_id
        )
        assert runtime.last_action_source == "exploration"


def test_exploration_sensorimotor_state_survives_runtime_checkpoint_roundtrip():
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    runtime = OrganismRuntime(
        organism_id="motor-exploration-runtime",
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        actuator_constitution=derive_actuator_constitution(8, physical_contract="unit-exploration-runtime-v2"),
        bootstrap_semantic_senses=False,
        discover_senses=False,
        min_samples=1,
    )

    for _ in range(24):
        runtime.tick()

    before = runtime.sensorimotor_snapshot
    assert before is not None
    assert before.exploration_coverage > 0.0

    payload = runtime.checkpoint()
    assert "exploration_mode" not in payload["actuation"]
    assert isinstance(payload["actuation"]["action_domain"]["competence_development"], dict)

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



def test_motor_percept_snapshot_preserves_complete_opaque_body_surface():
    from types import SimpleNamespace
    from symbiont.core.orchestration.runtime import OrganismRuntime

    runtime = OrganismRuntime.__new__(OrganismRuntime)
    runtime._sensory_system = SimpleNamespace(sensors=())
    percepts = tuple(
        SimpleNamespace(name=f"sense.{index:03d}", value=float(index))
        for index in range(96)
    )

    snapshot = runtime._motor_percept_snapshot(percepts)

    assert len(snapshot) == 96
    assert snapshot["sense.000"] == 0.0
    assert snapshot["sense.095"] == 95.0



def test_exploration_restore_rejects_missing_sensorimotor_checkpoint():
    from symbiont.host.checkpoint import CheckpointError

    runtime = _runtime()
    payload = runtime.checkpoint()
    assert isinstance(payload["actuation"]["action_domain"]["competence_development"], dict)
    del payload["actuation"]["action_domain"]["competence_development"]

    with pytest.raises(
        CheckpointError,
        match="missing competence_development",
    ):
        OrganismRuntime.from_checkpoint(
            payload,
            bootstrap_semantic_senses=False,
            discover_senses=False,
        )



def test_restore_rejects_removed_pending_primitive_verification_state():
    runtime = _runtime()
    payload = runtime.checkpoint()
    payload["actuation"]["pending_primitive_choice_context"] = {
        "primitive_id": "primitive.legacy",
        "concept_ids": ["concept.a"],
        "complete_tick": 12,
        "samples_before": 1,
    }

    from symbiont.host.checkpoint import CheckpointError

    with pytest.raises(CheckpointError, match="removed primitive verification state"):
        OrganismRuntime.from_checkpoint(
            payload,
            bootstrap_semantic_senses=False,
            discover_senses=False,
        )
