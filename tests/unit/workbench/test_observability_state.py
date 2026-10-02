"""Issue #277: every observability state of a cognitive panel is distinguishable.

The classifier is executed as the browser runs it. The organism-side lifecycle
status is tested against real runtimes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from symbiont.cognition.generative.budget import GenerativeBudget
from symbiont.cognition.generative.resident import ResidentGenerativeCognition
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont_lab.observation.projection import mind_snapshot_from_rich_state
from symbiont_lab.observation.subsystem_status import LIFECYCLES, generative_status

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "src/symbiont_lab/workbench/web/views/shared/observability-state.js"
LIVE = {"status": "live", "stale": False}
SNAPSHOT = {"transition_count": 2, "state_count": 3, "hypothesis_count": 1}
EMPTY_SNAPSHOT = {"transition_count": 0, "state_count": 1, "hypothesis_count": 0}
HAS_CONTENT = "(p) => (p.transition_count ?? 0) > 0"

CASES = [
    ("absent", {"status": {"lifecycle": "absent", "reason": "x"}, "stream": LIVE}),
    ("disabled", {"status": {"lifecycle": "disabled", "reason": "zero_budget"}, "stream": LIVE}),
    ("not_ready", {"status": {"lifecycle": "not_ready", "reason": "no_pass_yet"}, "stream": LIVE}),
    (
        "idle",
        {
            "status": {"lifecycle": "idle", "reason": "pass_without_work"},
            "payload": EMPTY_SNAPSHOT,
            "stream": LIVE,
        },
    ),
    ("empty", {"status": {"lifecycle": "active"}, "payload": EMPTY_SNAPSHOT, "stream": LIVE}),
    ("active", {"status": {"lifecycle": "active"}, "payload": SNAPSHOT, "stream": LIVE}),
    (
        "unavailable",
        {
            "status": {"lifecycle": "active"},
            "payload": SNAPSHOT,
            "stream": {"status": "disconnected", "stale": True},
        },
    ),
    ("unavailable", {"stream": LIVE}),
    (
        "stale",
        {
            "status": {"lifecycle": "active"},
            "payload": SNAPSHOT,
            "stream": {"status": "stale", "stale": True},
        },
    ),
    (
        "stale",
        {
            "status": {"lifecycle": "active"},
            "payload": SNAPSHOT,
            "stream": LIVE,
            "frameTick": 10,
            "liveTick": 40,
        },
    ),
    ("error", {"status": {"lifecycle": "running"}, "payload": SNAPSHOT, "stream": LIVE}),
    ("error", {"status": "active", "payload": SNAPSHOT, "stream": LIVE}),
    ("error", {"status": {"lifecycle": "active"}, "payload": [1, 2], "stream": LIVE}),
    ("error", {"status": {"lifecycle": "active"}, "stream": LIVE}),
    # A historical frame shown on purpose is judged by its own status, not by the stream.
    (
        "active",
        {
            "status": {"lifecycle": "active"},
            "payload": SNAPSHOT,
            "stream": {"status": "disconnected", "stale": True},
            "replay": True,
        },
    ),
    # Runs that predate the lifecycle status still show their snapshot.
    ("active", {"payload": SNAPSHOT, "stream": LIVE}),
]


def _classify(cases: list[dict]) -> list[dict]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the browser classifier")
    script = f"""
const {{classifyObservability, OBSERVABILITY_STATES}} = await import({json.dumps(MODULE.as_uri())});
const cases = {json.dumps(cases)};
const out = cases.map((input) => classifyObservability({{...input, hasContent: {HAS_CONTENT}}}));
console.log(JSON.stringify({{out, states: Object.values(OBSERVABILITY_STATES)}}));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_each_observability_state_is_reached_and_named() -> None:
    payload = _classify([case for _state, case in CASES])
    produced = [item["state"] for item in payload["out"]]

    assert produced == [state for state, _case in CASES]
    assert set(produced) == set(payload["states"])
    assert all(item["label"] and isinstance(item["current"], bool) for item in payload["out"])
    # Only states backed by a current frame may be presented as the present.
    current = {item["state"] for item in payload["out"] if item["current"]}
    assert current.isdisjoint({"unavailable", "stale", "error"})


def _organism(subsystem: object | None, tick: int = 5) -> SimpleNamespace:
    return SimpleNamespace(generative_cognition=subsystem, tick_count=tick)


def test_lifecycle_is_read_from_organism_facts() -> None:
    assert generative_status(SimpleNamespace())["lifecycle"] == "absent"

    disabled = ResidentGenerativeCognition(
        organism_id="o", budget=GenerativeBudget(max_model_queries=0)
    )
    assert generative_status(_organism(disabled))["lifecycle"] == "disabled"

    without_model = ResidentGenerativeCognition(organism_id="o")
    status = generative_status(_organism(without_model))
    assert (status["lifecycle"], status["reason"]) == ("not_ready", "no_generative_model")


def test_a_real_runtime_reports_a_known_lifecycle_before_and_after_ticking() -> None:
    runtime = OrganismRuntime(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)

    before = generative_status(runtime)
    for _ in range(3):
        runtime.tick()
    after = generative_status(runtime)

    assert before["lifecycle"] in LIFECYCLES and after["lifecycle"] in LIFECYCLES
    assert before["model_count"] >= 1
    assert before["lifecycle"] == "not_ready" and before["reason"] == "no_pass_yet"
    assert after["last_symbiont_tick"] == runtime.tick_count
    # A resident with a model that has nothing to anticipate is idle, not absent.
    assert (after["lifecycle"], after["reason"]) == ("idle", "pass_without_work")


def test_the_status_reaches_the_mind_snapshot_unaltered_even_when_malformed() -> None:
    for status in ({"lifecycle": "idle", "reason": "pass_without_work"}, "garbage"):
        snapshot = mind_snapshot_from_rich_state(
            {"tick": 3, "cognition": {"readouts": {}, "generative_status": status}}
        )
        assert snapshot["cognition"]["generativeStatus"] == status


def test_an_empty_data_panel_is_only_a_valid_empty_state_while_the_stream_is_live() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the browser classifier")
    script = f"""
const {{qualifyEmpty, applyEmptyState}} = await import({json.dumps(MODULE.as_uri())});
const live = qualifyEmpty('No milestones yet.', {{status: 'live', stale: false}});
const waiting = qualifyEmpty('No milestones yet.', {{status: 'waiting', stale: true}});
const stale = qualifyEmpty('No milestones yet.', {{status: 'stale', stale: true}});
const replay = qualifyEmpty('No milestones yet.', {{status: 'disconnected'}}, {{replay: true}});
const element = {{dataset: {{}}}};
const applied = applyEmptyState(element, 'No milestones yet.', {{status: 'stale', stale: true}});
console.log(JSON.stringify({{live, waiting, stale, replay, element, applied}}));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)

    assert out["live"] == {"state": "empty", "text": "No milestones yet."}
    assert out["replay"]["state"] == "empty"
    assert (
        out["waiting"]["state"] == "unavailable" and "No milestones" not in out["waiting"]["text"]
    )
    assert out["stale"]["state"] == "stale" and "No milestones yet." in out["stale"]["text"]
    assert out["applied"] == "stale" and out["element"]["dataset"]["observability"] == "stale"


def test_mind_panels_route_their_empty_states_through_the_contract() -> None:
    views = ROOT / "src/symbiont_lab/workbench/web/views/mind"
    assert (views / "history.js").read_text(encoding="utf-8").count("applyEmptyState(") == 2
    assert (views / "identity-sensory.js").read_text(encoding="utf-8").count(
        "applyEmptyState("
    ) == 4
    controller = (views / "cognition-controller.js").read_text(encoding="utf-8")
    assert "classifyObservability(" in controller
    assert "Generative resident not observed" not in controller
