"""Exact-replay state never persists real-host readings (CLAUDE.md: raw telemetry
is not persisted); deterministic synthetic subjects keep exact continuation."""

from __future__ import annotations

import json

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject

_REPLAY_KEYS = ("acclimation_replay", "rhythms_replay", "drift_replay")
_RAW_SENSOR_FIELDS = ("previous_input", "last_output", "integrator")


def _replay_fields(payload: dict) -> set[str]:
    found = {key for key in _REPLAY_KEYS if key in payload}
    if "replay_state" in (payload.get("sensory_development") or {}):
        found.add("sensory_development.replay_state")
    for sensor in (payload.get("sensory_system") or {}).get("sensors", []):
        found.update(f"sensor.{field}" for field in _RAW_SENSOR_FIELDS if field in sensor)
    return found


def test_real_host_checkpoint_carries_no_replay_state():
    runtime = OrganismRuntime(
        bootstrap_semantic_senses=True, discover_senses=True, min_samples=1, investigate_ticks=0
    )
    runtime.run(6)
    assert runtime._reading_providers  # the platform is actually read
    payload = runtime.checkpoint()
    assert _replay_fields(payload) == set()
    assert "previous_values" not in json.dumps(payload)


def test_synthetic_subject_checkpoint_keeps_exact_replay_state():
    body = CausalBody(actuator_count=2, seed=101)
    runtime = build_subject(body, organism_id="replay-boundary")
    for _ in range(6):
        runtime.tick()
        body.advance(runtime.last_actuations)
    fields = _replay_fields(runtime.checkpoint())
    assert {"acclimation_replay", "sensory_development.replay_state"} <= fields
