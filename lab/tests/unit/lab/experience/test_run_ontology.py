"""Experience & World run ontology (ADR-0008): kinds, termination, protection."""

from __future__ import annotations

import pytest

from lab.experience import (
    AcquisitionSafetyPolicy,
    RunGuard,
    RunKind,
    TerminationReason,
    WorldConsequencePolicy,
    resolve_termination,
    run_definition,
    run_definition_catalog,
)


def test_run_kinds_separate_acquisition_from_world() -> None:
    assert RunKind.ACQUISITION_EMBODIMENT.is_acquisition
    assert RunKind.ACQUISITION_VISION.is_acquisition
    assert not RunKind.WORLD_CHALLENGE.is_acquisition
    assert not RunKind.WORLD_OPEN.is_acquisition


def test_acquisition_terminates_before_irreversible_viability_loss() -> None:
    policy = AcquisitionSafetyPolicy()
    assert policy.assess(alive=True, vital_state="active") is None
    assert policy.assess(alive=True, vital_state="stressed") is None
    for severe in ("agonizing", "dormant"):
        assert policy.assess(alive=True, vital_state=severe) is TerminationReason.PROTECTED_RECOVERY
    # A death that skips the boundary is a breach, never masked as recovery.
    assert policy.assess(alive=False, vital_state="dead") is TerminationReason.BODY_NON_VIABLE


def test_world_never_rescues_the_body() -> None:
    policy = WorldConsequencePolicy()
    for state in ("active", "stressed", "agonizing", "dormant"):
        assert policy.assess(alive=True, vital_state=state) is None
    assert policy.assess(alive=False, vital_state="dead") is TerminationReason.BODY_NON_VIABLE


def test_guard_reports_exit_cause_and_remembers_trigger() -> None:
    guard = RunGuard(RunKind.ACQUISITION_EMBODIMENT)
    assert guard(True, "active") is None
    assert guard(True, "agonizing") == "guard:protected_recovery"
    assert guard.triggered is TerminationReason.PROTECTED_RECOVERY


@pytest.mark.parametrize(
    ("kind", "cause", "failed", "expected"),
    [
        (RunKind.ACQUISITION_EMBODIMENT, "budget_exhausted", False, "time_budget_reached"),
        (RunKind.WORLD_CHALLENGE, "budget_exhausted", False, "world_duration_complete"),
        (RunKind.WORLD_OPEN, "operator_stop", False, "operator_stop"),
        (RunKind.WORLD_OPEN, "body_non_viable", False, "body_non_viable"),
        (RunKind.ACQUISITION_EMBODIMENT, "guard:protected_recovery", False, "protected_recovery"),
        (RunKind.WORLD_OPEN, "physics_disconnected", False, "technical_failure"),
        (RunKind.WORLD_OPEN, "error", True, "technical_failure"),
        (RunKind.WORLD_OPEN, None, True, "technical_failure"),
        (RunKind.WORLD_OPEN, None, False, "operator_stop"),
    ],
)
def test_exit_cause_maps_to_kind_specific_termination(kind, cause, failed, expected) -> None:
    assert resolve_termination(kind, cause, failed=failed).value == expected


def test_termination_taxonomy_has_no_win_or_loss() -> None:
    values = {item.value for item in TerminationReason}
    assert not values & {"won", "lost", "win", "loss", "success", "failure"}


def test_catalog_definitions_carry_no_goal_or_reward() -> None:
    forbidden = ("goal", "reward", "route", "win", "success", "target")
    for item in run_definition_catalog():
        text = repr(item).lower()
        for word in forbidden:
            assert f"'{word}" not in text, (item["definition_id"], word)


def test_vision_requires_the_visual_apparatus_body() -> None:
    # ADR-0011: launchable only together with the causal VisualApparatus body.
    vision = run_definition("vision-nursery-v1")
    assert vision.kind is RunKind.ACQUISITION_VISION
    assert vision.launchable
    assert vision.body_kind == "anthropomorphic-v6-vision"
    assert vision.environment == "vision-nursery-v1"


def test_default_definition_preserves_pre_ontology_open_world() -> None:
    default = run_definition(None)
    assert default.kind is RunKind.WORLD_OPEN
    assert default.environment is None


def test_unknown_definition_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown run definition"):
        run_definition("walk-to-goal-v1")
