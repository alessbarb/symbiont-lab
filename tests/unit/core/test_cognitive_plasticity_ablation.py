"""Vision Acquisition v1 arm B: the Lab ablation stops cognitive acquisition
without touching sensor admission, and is never persisted."""

from __future__ import annotations

from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject


def _run(ablated: bool, ticks: int = 120):
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="ablation")
    runtime.cognitive_plasticity_ablated = ablated
    start = runtime.checkpoint()
    for _ in range(ticks):
        runtime.tick(include_observability=False)
        body.advance(runtime.last_actuations)
    return runtime, start


def _learned(runtime) -> tuple[int, int]:
    graph = runtime.checkpoint()["cognitive_bridge"]["graph"]
    predictors = sum(1 for node in graph["nodes"] if node.get("kind") == "predictor")
    return predictors, len(graph["edges"])


def _sensor_sources(runtime) -> list[tuple[str, ...]]:
    return sorted(tuple(sensor.source_ids) for sensor in runtime._sensory_system.sensors)


def test_ablation_keeps_sensor_admission_but_freezes_cognitive_graph() -> None:
    normal, _ = _run(False)
    ablated, _ = _run(True)

    assert _sensor_sources(ablated) == _sensor_sources(normal)
    # Senses still enter cognition as nodes; no learned structure forms.
    assert _learned(ablated) == (0, 0)
    assert _learned(normal) != (0, 0)


def test_ablation_is_not_persisted() -> None:
    ablated, _ = _run(True, ticks=4)
    payload = ablated.checkpoint()
    assert "cognitive_plasticity_ablated" not in repr(payload)
