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
    ConsolidationGate,
    _prepare_acquired,
    _relation_classes,
    _twin,
    run_acquisition_reuse_closure_study,
    run_consolidated_causal_intervention_study,
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
    "agency-consolidated-causal-intervention": (
        "learning.agency-consolidated-causal-intervention",
        "run_consolidated_causal_intervention_study",
    ),
    "agency-high-dimensional-acquisition": (
        "learning.agency-high-dimensional-acquisition",
        "run_high_dimensional_acquisition_study",
    ),
    "agency-intentional-causal-advantage": (
        "learning.agency-intentional-causal-advantage",
        "run_intentional_causal_advantage_study",
    ),
    "agency-acquisition-reuse-closure": (
        "learning.agency-acquisition-reuse-closure",
        "run_acquisition_reuse_closure_study",
    ),
    "agency-acquisition-reuse-closure-factorized": (
        "learning.agency-acquisition-reuse-closure",
        "run_acquisition_reuse_closure_study",
    ),
}


def test_agency_protocols_are_registered():
    for protocol, function_name in PROTOCOLS.values():
        assert get_protocol(protocol).__name__ == function_name


BASE_SEEDS = (101, 127, 149)
EXECUTIVE_SEEDS = BASE_SEEDS + (163, 179, 193, 211, 227, 241, 257)
CONSOLIDATED_SEEDS = EXECUTIVE_SEEDS + (271, 283, 307, 311, 331, 347, 359, 373, 389, 401)
EXECUTIVE_STUDIES = {
    "agency-high-dimensional-acquisition",
    "agency-consolidated-causal-intervention",
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
        if directory == "agency-consolidated-causal-intervention":
            expected = CONSOLIDATED_SEEDS
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


def test_e5_v3_isolates_executive_outcome_learning_in_arm_d():
    from symbiont_lab.studies.learning.agency_acquisition import (
        run_executive_bridge_ablation_study,
        run_intentional_causal_advantage_study,
    )

    e5 = run_intentional_causal_advantage_study(seeds=(127,), warmup_limit=400, horizon_ticks=4)
    (row,) = e5["per_seed"]
    enabled = {name: arm["outcome_learning"]["enabled"] for name, arm in row["arms"].items()}
    assert enabled == {
        "A_direct_proposal": False,
        "B_unreconciled_intent": False,
        "C_reconciled_intent": False,
        "D_reconciled_intent_outcome_learning": True,
    }
    for arm in row["arms"].values():
        assert set(arm["outcome_learning"]) == {"enabled", "at_split", "at_end"}
    e2 = run_executive_bridge_ablation_study(seeds=(127,), warmup_limit=400, horizon_ticks=4)
    assert set(e2["per_seed"][0]["arms"]) == {
        "direct_proposal",
        "action_intent",
        "action_intent_outcome_learning",
    }


def test_consolidated_intervention_waits_for_the_gate_and_reports_every_horizon():
    loose = ConsolidationGate(
        min_support=1,
        min_controllability=0.0,
        min_agency=0.0,
        stability_ticks=2,
        max_wait_ticks=400,
    )
    result = run_consolidated_causal_intervention_study(
        seeds=(101,), warmup_limit=600, gate=loose, horizons=(4, 8), primary_horizon=8
    )
    (row,) = result["per_seed"]
    broken = row["conditions"]["broken_effector"]
    assert broken["onset_tick"] >= row["acquired_at_tick"] + loose.stability_ticks
    assert broken["gated_relations"] >= 1
    assert set(broken["horizons"]) == {"4", "8"}
    for point in broken["horizons"].values():
        assert set(point) >= {"perturbed", "normal_control", "residual_controllability_gap"}
    summary = result["summary"]["broken_effector"]
    assert summary["by_horizon"]["8"]["testable_seeds"] == 1
    assert isinstance(summary["primary_endpoint_supported"], bool)


def test_consolidated_intervention_respects_the_minimum_developmental_age():
    aged = ConsolidationGate(
        min_support=1,
        min_controllability=0.0,
        min_agency=0.0,
        stability_ticks=2,
        max_wait_ticks=400,
        min_age_ticks=50,
    )
    result = run_consolidated_causal_intervention_study(
        seeds=(101,), warmup_limit=600, gate=aged, horizons=(4,), primary_horizon=4
    )
    (row,) = result["per_seed"]
    onset = row["conditions"]["broken_effector"]["onset_tick"]
    assert onset >= row["acquired_at_tick"] + aged.min_age_ticks + aged.stability_ticks
    with pytest.raises(ValueError):
        run_consolidated_causal_intervention_study(
            seeds=(101,),
            warmup_limit=600,
            gate=ConsolidationGate(max_wait_ticks=8, min_age_ticks=8),
            horizons=(4,),
            primary_horizon=4,
        )


def test_consolidated_intervention_marks_ungated_seeds_untestable():
    strict = ConsolidationGate(min_controllability=2.0, max_wait_ticks=8)
    result = run_consolidated_causal_intervention_study(
        seeds=(127,), warmup_limit=400, gate=strict, horizons=(4,), primary_horizon=4
    )
    assert result["per_seed"][0]["conditions"] == {}
    assert result["summary"]["broken_effector"]["by_horizon"]["4"]["testable_seeds"] == 0
    assert result["summary"]["broken_effector"]["primary_endpoint_supported"] is False
    with pytest.raises(ValueError):
        run_consolidated_causal_intervention_study(seeds=(127,), horizons=(4,), primary_horizon=8)


def test_high_dimensional_body_keeps_the_default_body_and_adds_correlation_and_drift():
    from symbiont.actuation.types import Actuation

    default = CausalBody(actuator_count=4, seed=7)
    assert default.receptors_per_actuator == 1 and default.drifting_count == 0
    for actuator_id in default.surface.actuator_ids:
        assert default.driven_receptors(actuator_id) == (default.driven_receptor(actuator_id),)

    body = CausalBody(actuator_count=4, seed=7, receptors_per_actuator=4, drifting_receptor_count=8)
    assert len(body.receptor_ids) == 4 * 4 + 8 + 1
    first = body.surface.actuator_ids[0]
    driven = body.driven_receptors(first)
    assert len(driven) == 4
    body.advance((Actuation(actuator_id=first, requested=1.0, delivered=1.0),))
    rises = [body._values[receptor] - 0.5 for receptor in driven]
    assert rises == sorted(rises, reverse=True) and rises[-1] > 0.0
    still = CausalBody(
        actuator_count=4, seed=7, receptors_per_actuator=4, drifting_receptor_count=8
    )
    for _ in range(5):
        still.advance(())
    assert any(still._values[receptor] != 0.5 for receptor in still._drifting_ids)
    still.set_condition(BodyCondition.BROKEN_EFFECTOR)
    assert still.driven_receptors(first) == ()


def test_high_dimensional_acquisition_study_reports_the_chain():
    from symbiont_lab.studies.learning.agency_acquisition import (
        run_high_dimensional_acquisition_study,
    )

    result = run_high_dimensional_acquisition_study(
        seeds=(101,),
        ticks=20,
        actuator_count=4,
        receptors_per_actuator=2,
        drifting_receptor_count=4,
    )
    (row,) = result["per_seed"]
    assert row["receptors"] == 4 * 2 + 4 + 1
    for key in (
        "recurring_effect_fraction",
        "competences_with_effect",
        "execution_bindings",
        "intents_satisfied",
    ):
        assert key in row


@pytest.mark.experiment_contract
def test_e8_v3_arms_differ_only_in_reconciliation():
    root = Path(__file__).resolve().parents[3] / "experiments" / "learning"
    r = load_experiment_file(root / "agency-intent-reconciliation-r" / "experiment.toml")
    ab = load_experiment_file(root / "agency-intent-reconciliation-ab" / "experiment.toml")
    gate = load_experiment_file(
        root / "agency-acquisition-reuse-closure-chance-corrected" / "experiment.toml"
    )
    assert r.protocol == ab.protocol == "learning.agency-high-dimensional-acquisition"
    assert tuple(r.seeds) == tuple(ab.seeds) == EXECUTIVE_SEEDS and r.steps == ab.steps == 3000
    assert r.extra_params["body"] == ab.extra_params["body"]
    assert r.extra_params["ablation"] == {"factorized_effects": True, "reconciliation": "recall"}
    assert ab.extra_params["ablation"] == {
        "factorized_effects": True,
        "reconciliation": "chance_corrected",
    }
    assert gate.protocol == "learning.agency-acquisition-reuse-closure"
    assert tuple(gate.seeds) == BASE_SEEDS
    assert gate.extra_params["ablation"]["reconciliation"] == "chance_corrected"


@pytest.mark.experiment_contract
def test_e8_v3_reports_terminations_and_spurious_satisfactions():
    from symbiont_lab.studies.learning.agency_acquisition import (
        run_high_dimensional_acquisition_study,
    )

    result = run_high_dimensional_acquisition_study(
        seeds=(101,),
        ticks=20,
        actuator_count=4,
        receptors_per_actuator=2,
        drifting_receptor_count=4,
        factorized_effects=True,
        reconciliation="chance_corrected",
    )
    (row,) = result["per_seed"]
    assert result["reconciliation"] == "chance_corrected"
    for key in ("satisfied_rate", "terminal_reasons", "spurious_satisfactions"):
        assert key in row
    assert row["unmapped_matched_atoms"] == 0
    with pytest.raises(ValueError):
        run_high_dimensional_acquisition_study(seeds=(101,), ticks=1, reconciliation="other")


@pytest.mark.experiment_contract
def test_fp0_classifies_members_and_reports_the_decision_inputs():
    from symbiont_lab.studies.learning.footprint_precision import run_footprint_precision_study

    root = Path(__file__).resolve().parents[3] / "experiments" / "learning"
    spec = load_experiment_file(root / "footprint-precision" / "experiment.toml")
    assert spec.protocol == "learning.footprint-precision"
    assert tuple(spec.seeds) == EXECUTIVE_SEEDS and spec.steps == 3000
    assert get_protocol("learning.footprint-precision") is run_footprint_precision_study

    result = run_footprint_precision_study(
        seeds=(101,), ticks=400, actuator_count=4, receptors_per_actuator=2,
        drifting_receptor_count=4,
    )  # fmt: skip
    (row,) = result["per_seed"]
    snapshot = row["snapshots"]["400"]
    assert set(snapshot["by_class"]) == {"own", "cross", "drift", "other"}
    assert snapshot["members"] == sum(snapshot["by_class"].values())
    assert set(result["decision_inputs"]) >= {"wrong_members", "selected_hypothesis"}


@pytest.mark.experiment_contract
def test_runner_records_fp0_results(tmp_path):
    # Regression: the runner branch once dropped the result, losing a full run.
    spec = spec_from_payload(
        {
            "id": "test.footprint-precision",
            "protocol": "learning.footprint-precision",
            "steps": 24,
            "seeds": [7],
            "body": {
                "actuator_count": 4,
                "receptors_per_actuator": 2,
                "drifting_receptor_count": 4,
            },
        }
    )
    _result, _manifest, run_dir = ExperimentRunner(base_dir=tmp_path / ".symbiont").run(spec)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["protocol"] == "learning.footprint-precision"
    assert metrics["seeds"] == [7] and "decision_inputs" in metrics
    assert metrics["membership"] == "R"


@pytest.mark.experiment_contract
def test_fp1_arms_differ_only_in_membership():
    root = Path(__file__).resolve().parents[3] / "experiments" / "learning"
    arms = {
        arm: load_experiment_file(root / f"footprint-precision-fp1-{arm}" / "experiment.toml")
        for arm in ("r", "t", "m", "tm")
    }
    for arm, spec in arms.items():
        assert spec.protocol == "learning.footprint-precision"
        assert tuple(spec.seeds) == EXECUTIVE_SEEDS and spec.steps == 3000
        assert spec.extra_params["ablation"] == {"membership": arm.upper()}
        assert spec.extra_params["body"] == arms["r"].extra_params["body"]
    for arm in ("t", "m", "tm"):
        gate = load_experiment_file(
            root / f"agency-acquisition-reuse-closure-membership-{arm}" / "experiment.toml"
        )
        assert tuple(gate.seeds) == BASE_SEEDS
        assert gate.extra_params["ablation"] == {
            "factorized_effects": True,
            "membership": arm.upper(),
        }


@pytest.mark.experiment_contract
def test_fp2_runs_on_new_seeds_disjoint_from_its_design_data():
    root = Path(__file__).resolve().parents[3] / "experiments" / "learning"
    design_seeds = set(EXECUTIVE_SEEDS)
    for arm in ("r", "m", "bh"):
        spec = load_experiment_file(root / f"footprint-precision-fp2-{arm}" / "experiment.toml")
        assert spec.extra_params["ablation"] == {"membership": arm.upper()}
        assert len(spec.seeds) == 10 and not set(spec.seeds) & design_seeds
    gate = load_experiment_file(
        root / "agency-acquisition-reuse-closure-membership-bh" / "experiment.toml"
    )
    assert gate.extra_params["ablation"]["membership"] == "BH"


@pytest.mark.experiment_contract
def test_bd1_arms_and_runner(tmp_path):
    root = Path(__file__).resolve().parents[3] / "experiments" / "learning"
    used = set(EXECUTIVE_SEEDS) | {463, 467, 479, 487, 491, 499, 503, 509, 521, 523}
    for arm in ("OFF", "HIST"):
        spec = load_experiment_file(root / f"binding-degradation-{arm.lower()}" / "experiment.toml")
        assert spec.extra_params["ablation"] == {"arm": arm, "break_tick": 2000}
        assert spec.steps == 4000 and not set(spec.seeds) & used
    gate = load_experiment_file(
        root / "agency-acquisition-reuse-closure-binding-history" / "experiment.toml"
    )
    assert gate.extra_params["ablation"]["binding_invalidation"] == "history"
    spec = spec_from_payload(
        {
            "id": "test.binding-degradation",
            "protocol": "learning.binding-degradation",
            "steps": 30,
            "seeds": [7],
            "body": {
                "actuator_count": 4,
                "receptors_per_actuator": 2,
                "drifting_receptor_count": 4,
            },
            "ablation": {"arm": "HIST", "break_tick": 15},
        }
    )
    _result, _manifest, run_dir = ExperimentRunner(base_dir=tmp_path / ".symbiont").run(spec)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["protocol"] == "learning.binding-degradation" and metrics["arm"] == "HIST"
