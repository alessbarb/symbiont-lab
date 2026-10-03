"""Lab-owned cognitive acquisition ablation (Visual Acquisition v1 arm B).

The ablation stops cognitive acquisition without touching sensor admission and
uses only neutral runtime switches. The switches are apparatus configuration,
not organism state: they never enter state identity, but their effective values
are recorded as provenance and reapplied on restart (Longitudinal Integrity v1
§9), so an ablated arm stays ablated across a process boundary.
"""

from __future__ import annotations

from lab.studies.ablations import CognitiveAcquisitionAblation
from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject


def _run(ablation: CognitiveAcquisitionAblation | None, ticks: int = 120):
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="ablation")
    if ablation is not None:
        ablation.apply(runtime)
    for _ in range(ticks):
        runtime.tick(include_observability=False)
        body.advance(runtime.last_actuations)
    return runtime


def _learned(runtime) -> tuple[int, int]:
    graph = runtime.checkpoint()["cognitive_bridge"]["graph"]
    predictors = sum(1 for node in graph["nodes"] if node.get("kind") == "predictor")
    return predictors, len(graph["edges"])


def _sensor_sources(runtime) -> list[tuple[str, ...]]:
    return sorted(tuple(sensor.source_ids) for sensor in runtime._sensory_system.sensors)


def test_ablation_keeps_sensor_admission_but_stops_learned_structure() -> None:
    normal = _run(None)
    ablated = _run(CognitiveAcquisitionAblation())
    assert _sensor_sources(ablated) == _sensor_sources(normal)
    # Senses still enter cognition as nodes; no learned structure forms.
    assert _learned(ablated) == (0, 0)
    assert _learned(normal) != (0, 0)


def test_ablation_is_configuration_not_organism_state() -> None:
    runtime = _run(None, ticks=4)
    identity = runtime.state_hash()

    CognitiveAcquisitionAblation().apply(runtime)

    assert runtime.state_hash() == identity
    assert "predictor_promotion" not in repr(runtime.checkpoint()["effective_config"])


def test_ablated_arm_stays_ablated_across_a_restart() -> None:
    ablated = _run(CognitiveAcquisitionAblation(), ticks=4)
    payload = ablated.checkpoint()
    controls = payload["runtime_provenance"]["session_controls"]
    assert controls["cognitive_plasticity_enabled"] is False
    assert controls["predictor_promotion_enabled"] is False

    restored = type(ablated).from_checkpoint(payload)

    assert restored._cognitive_plasticity_enabled is False
    assert restored._predictor_promotion_enabled is False


def test_unablated_state_restores_enabled_so_an_arm_can_be_applied_after_restore() -> None:
    normal = _run(None, ticks=4)

    restored = type(normal).from_checkpoint(normal.checkpoint())

    assert restored._cognitive_plasticity_enabled is True
    assert restored._predictor_promotion_enabled is True
