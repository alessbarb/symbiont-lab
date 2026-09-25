"""L6.6 — opaque interoception is ordinary sensorimotor evidence.

No separate mechanism routes interoceptive channels into sensorimotor
learning: ``_sensorimotor_body_snapshot``/``_motor_percept_snapshot`` take
whatever the sensory system currently exposes, filtering out only motor
command echoes. Interoceptive percepts flow through the identical opaque
percept pipeline as everything else (L3), so when interoception is enabled
they are simply part of the same body_state ordinary evidence already
feeding primitive formation and actuator causal-evidence tracking.
"""
from __future__ import annotations

from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits
from symbiont.core.runtime import OrganismDeadError, OrganismRuntime


def _reproduction_genome():
    return load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=(0, 80, 0),
    )


def _runtime(interoception_mode: str) -> OrganismRuntime:
    return OrganismRuntime(
        organism_id="interoception-coupling-probe",
        genome=_reproduction_genome(),
        actuation_enabled=True,
        actuator_constitution=derive_actuator_constitution(8, physical_contract="interoception-probe-v2"),
        bootstrap_semantic_senses=True,
        discover_senses=True,
        min_samples=1,
        investigate_ticks=0,
        interoception_mode=interoception_mode,
    )


def _capture_snapshot_sizes(runtime: OrganismRuntime, method_name: str, ticks: int) -> list[int]:
    captured: list[int] = []
    original = getattr(runtime, method_name)

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.append(len(result))
        return result

    setattr(runtime, method_name, wrapper)
    for _ in range(ticks):
        try:
            runtime.tick()
        except OrganismDeadError:
            break
    return captured


def test_interoception_enabled_widens_sensorimotor_body_state():
    on_sizes = _capture_snapshot_sizes(
        _runtime("enabled"), "_sensorimotor_body_snapshot", ticks=40
    )
    off_sizes = _capture_snapshot_sizes(
        _runtime("absent"), "_sensorimotor_body_snapshot", ticks=40
    )
    assert on_sizes and off_sizes
    assert max(on_sizes) > max(off_sizes)


def test_interoception_enabled_widens_actuator_effect_percept_snapshot():
    """The same generic filtering feeds ActuatorEvidenceModel.record_effect's
    percept snapshot — interoceptive channels can drive actuator causal
    promotion too, not only exteroceptive ones."""
    on_sizes = _capture_snapshot_sizes(
        _runtime("enabled"), "_motor_percept_snapshot", ticks=40
    )
    off_sizes = _capture_snapshot_sizes(
        _runtime("absent"), "_motor_percept_snapshot", ticks=40
    )
    assert on_sizes and off_sizes
    assert max(on_sizes) > max(off_sizes)


def test_sensorimotor_primitive_formation_is_channel_identity_agnostic():
    """Direct proof at the learner level: a reproducible motor->body-state
    regularity becomes a reusable primitive regardless of whether the
    responding channel is named like an interoceptive signal or anything
    else — CompetenceDevelopmentEngine never special-cases channel identity."""
    from symbiont.actuation.sensorimotor import CompetenceDevelopmentEngine

    learner = CompetenceDevelopmentEngine(
        tuple(f"actuator.{i}" for i in range(4)),
        organism_id="org-interoceptive-primitive",
        max_concurrent=4,
    )
    sequence = (
        {"actuator.0": 0.7, "actuator.1": 0.3},
        {"actuator.0": 0.5, "actuator.2": 0.6},
        {"actuator.1": 0.6, "actuator.3": 0.4},
        {"actuator.0": 0.3, "actuator.2": 0.7, "actuator.3": 0.2},
    )
    state = {"interoceptive.channel_7": 0.0}
    tick = 0
    for episode_index in range(2):
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
                "interoceptive.channel_7": state["interoceptive.channel_7"]
                + drive * 0.01 * signed
            }
            tick += 1
        learner.observe(
            tick=tick,
            body_state=state,
            motor_vector={},
            discovery_eligible=False,
        )
        tick += 1
        if episode_index == 0:
            while tick % 8:
                learner.observe(
                    tick=tick,
                    body_state=state,
                    motor_vector={},
                    discovery_eligible=False,
                )
                tick += 1

    assert learner.primitives
    assert learner.cognitive_primitives
