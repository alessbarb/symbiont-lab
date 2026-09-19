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
