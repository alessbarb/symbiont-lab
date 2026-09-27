"""Mechanical contracts of the Agency Acquisition v1 protocols E1-E6 (§112-§117).

These tests check registration, preregistration binding and runner plumbing
on tiny budgets.  They establish no scientific conclusion.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont.actuation.intervention import opaque_channel_ref
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.experiments.spec import spec_from_payload
from symbiont_lab.studies.learning.agency_acquisition import (
    _prepare_acquired,
    _relation_classes,
    _twin,
    run_acquisition_reuse_closure_study,
)
from symbiont_lab.studies.learning.agency_acquisition_body import (
    BodyCondition,
    CausalBody,
    build_subject,
)

pytestmark = pytest.mark.experiment_contract

PROTOCOLS = {
    "agency-acquisition-ablation": (
        "learning.agency-acquisition-ablation",
        "run_agency_acquisition_ablation_study",
    ),
    "agency-executive-bridge-ablation": (
        "learning.agency-executive-bridge-ablation",
        "run_executive_bridge_ablation_study",
    ),
    "agency-intent-persistence": (
        "learning.agency-intent-persistence",
        "run_intent_persistence_study",
    ),
    "agency-embodied-causal-intervention": (
        "learning.agency-embodied-causal-intervention",
        "run_embodied_causal_intervention_study",
    ),
    "agency-intentional-causal-advantage": (
        "learning.agency-intentional-causal-advantage",
        "run_intentional_causal_advantage_study",
    ),
    "agency-acquisition-reuse-closure": (
        "learning.agency-acquisition-reuse-closure",
        "run_acquisition_reuse_closure_study",
    ),
}


def test_agency_protocols_are_registered():
    for protocol, function_name in PROTOCOLS.values():
        assert get_protocol(protocol).__name__ == function_name


BASE_SEEDS = (101, 127, 149)
EXECUTIVE_SEEDS = BASE_SEEDS + (163, 179, 193, 211, 227, 241, 257)
EXECUTIVE_STUDIES = {
    "agency-executive-bridge-ablation",
    "agency-intent-persistence",
    "agency-intentional-causal-advantage",
}


def test_agency_preregistrations_bind_expected_protocols():
    root = Path("experiments/learning")
    for directory, (protocol, _function) in PROTOCOLS.items():
        spec = load_experiment_file(root / directory / "experiment.toml")
        assert spec.protocol == protocol
        expected = EXECUTIVE_SEEDS if directory in EXECUTIVE_STUDIES else BASE_SEEDS
        assert tuple(spec.seeds) == expected
        assert (root / directory / "README.md").is_file()


@pytest.mark.parametrize("directory", sorted(PROTOCOLS))
def test_runner_executes_each_protocol_on_declared_seeds(directory, tmp_path):
    protocol, _function = PROTOCOLS[directory]
    spec = spec_from_payload(
        {
            "id": f"test.{directory}",
            "protocol": protocol,
            "steps": 24,
            "seeds": [7],
            "ablation": {"horizon_ticks": 4, "inert_actuator_count": 1},
        }
    )
    _result, manifest, run_dir = ExperimentRunner(base_dir=tmp_path / ".symbiont").run(spec)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["protocol"] == protocol
    assert metrics["seeds"] == [7]
    assert manifest.config["seeds"] == [7]


def test_matched_studies_mark_unacquired_seeds_as_not_testable(tmp_path):
    spec = spec_from_payload(
        {
            "id": "test.not-testable",
            "protocol": "learning.agency-intentional-causal-advantage",
            "steps": 5,
            "seeds": [7],
            "ablation": {"horizon_ticks": 4},
        }
    )
    _result, _manifest, run_dir = ExperimentRunner(base_dir=tmp_path / ".symbiont").run(spec)
    (row,) = json.loads((run_dir / "metrics.json").read_text())["per_seed"]
    assert row["acquired_at_tick"] is None and row["arms"] == {}
    assert row["testable"] is False


def test_agency_studies_are_deterministic_and_seed_validated():
    # Long enough for the executive loop to engage and close (seed 127).
    first = run_acquisition_reuse_closure_study(seeds=(127,), max_ticks=600)
    second = run_acquisition_reuse_closure_study(seeds=(127,), max_ticks=600)
    assert first == second
    assert first["per_seed"][0]["closed"] is True
    with pytest.raises(ValueError):
        run_acquisition_reuse_closure_study(seeds=(), max_ticks=10)
    with pytest.raises(ValueError):
        run_acquisition_reuse_closure_study(seeds=(1, 1), max_ticks=10)


def test_matched_twins_are_identical_continuations():
    body = CausalBody(actuator_count=4, seed=7)
    runtime = build_subject(body, organism_id="twin-contract")
    for _ in range(200):
        runtime.tick()
        body.advance(runtime.last_actuations)
    first, first_body = _twin(runtime, body)
    second, second_body = _twin(runtime, body)
    for _ in range(200):
        first.tick()
        first_body.advance(first.last_actuations)
        second.tick()
        second_body.advance(second.last_actuations)
    assert (
        first._action_domain.causal_evidence.evidence
        == second._action_domain.causal_evidence.evidence
    )


def test_e4_relation_classes_follow_the_physical_ground_truth():
    runtime, body, acquired_at = _prepare_acquired(
        101, actuator_count=4, warmup_limit=600, settle_ticks=64
    )
    assert acquired_at is not None
    registry = runtime._action_domain.acquisition.action_dimensions
    broken_channel = opaque_channel_ref(body.surface.actuator_ids[0])

    unchanged_lost, _ = _relation_classes(runtime, body, BodyCondition.NORMAL)
    assert unchanged_lost == set()

    invalidated, intact = _relation_classes(runtime, body, BodyCondition.BROKEN_EFFECTOR)
    assert invalidated and intact
    assert not invalidated & intact
    # Only relations of dimensions driving the broken output can be invalidated.
    assert all(broken_channel in registry.channel_refs(dim) for dim, _effect in invalidated)
    # Classification is evaluator-only: it never changes the organism.
    assert body.condition is BodyCondition.NORMAL
