"""Lab-owned cognitive acquisition ablation (Visual Acquisition v1 arm B).

The ablation stops cognitive acquisition without touching sensor admission,
uses only neutral runtime switches, and is never persisted.
"""

from __future__ import annotations

from symbiont_lab.studies.ablations import CognitiveAcquisitionAblation
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject


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


def test_ablation_is_not_persisted_and_restores_as_enabled() -> None:
    ablated = _run(CognitiveAcquisitionAblation(), ticks=4)
    payload = ablated.checkpoint()
    assert "predictor_promotion" not in repr(payload)
    restored = type(ablated).from_checkpoint(payload)
    assert restored._cognitive_plasticity_enabled is True
    assert restored._predictor_promotion_enabled is True
