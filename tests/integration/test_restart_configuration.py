"""Longitudinal Integrity v1 §9: runtime-only configuration is recorded and reapplied."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from symbiont.agency.prospective import ExecutiveAdmissionPolicy
from symbiont.cognition.limits import KernelLimits
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import CheckpointError
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

RUNTIME_KWARGS = dict(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)


def _saved(runtime: OrganismRuntime) -> dict:
    return json.loads(json.dumps(runtime.checkpoint()))


def _controls(payload: dict) -> dict:
    return payload["runtime_provenance"]["session_controls"]


@pytest.mark.parametrize("runtime_type", [OrganismRuntime, PrivateModelOrganismRuntime])
def test_disabled_learning_switches_survive_restart(runtime_type) -> None:
    runtime = runtime_type(**RUNTIME_KWARGS)
    runtime.tick()
    runtime.set_cognitive_plasticity_enabled(False)
    runtime.set_predictor_promotion_enabled(False)
    saved = _saved(runtime)
    assert _controls(saved)["cognitive_plasticity_enabled"] is False
    assert _controls(saved)["predictor_promotion_enabled"] is False

    restored = runtime_type.from_checkpoint(saved, **RUNTIME_KWARGS)

    assert restored._cognitive_plasticity_enabled is False
    assert restored._predictor_promotion_enabled is False
    assert _saved(restored)["runtime_provenance"] == saved["runtime_provenance"]


def test_recorded_controls_do_not_change_state_identity() -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    before = runtime.state_hash()
    runtime.set_cognitive_plasticity_enabled(False)

    assert runtime.state_hash() == before


def test_launcher_supplied_limits_and_policy_are_reapplied() -> None:
    limits = replace(KernelLimits(), reacclimation_ticks=KernelLimits().reacclimation_ticks + 3)
    policy = ExecutiveAdmissionPolicy(readout_threshold=0.3, minimum_relevance=0.4)
    runtime = OrganismRuntime(
        **RUNTIME_KWARGS,
        kernel_limits=limits,
        executive_admission_policy=policy,
        persist_replay_state=False,
    )
    runtime.tick()

    restored = OrganismRuntime.from_checkpoint(_saved(runtime), **RUNTIME_KWARGS)

    assert restored._kernel_limits == limits
    assert restored._executive_admission_policy == policy
    assert restored._persist_replay_state is False
    assert _saved(restored)["runtime_provenance"]["changed_since_restore"] == []


def test_a_different_continuation_is_recorded_as_a_changed_condition() -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    saved = _saved(runtime)

    restored = OrganismRuntime.from_checkpoint(
        saved,
        **RUNTIME_KWARGS,
        executive_admission_policy=ExecutiveAdmissionPolicy(readout_threshold=0.5),
    )
    restored.set_predictor_promotion_enabled(False)

    assert _saved(restored)["runtime_provenance"]["changed_since_restore"] == [
        "executive_admission_policy",
        "predictor_promotion_enabled",
    ]


def test_checkpoint_without_recorded_controls_restores_with_defaults() -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    saved = _saved(runtime)
    del saved["runtime_provenance"]["session_controls"]
    del saved["runtime_provenance"]["changed_since_restore"]

    restored = OrganismRuntime.from_checkpoint(saved, **RUNTIME_KWARGS)

    assert restored._cognitive_plasticity_enabled is True
    assert restored._predictor_promotion_enabled is True
    assert _saved(restored)["runtime_provenance"]["changed_since_restore"] == []


@pytest.mark.parametrize(
    "controls",
    [
        [],
        {"cognitive_plasticity_enabled": "no"},
        {"predictor_promotion_enabled": 0},
        {"persist_replay_state": "yes"},
        {"kernel_limits": {"not_a_limit": 1}},
        {"executive_admission_policy": {"readout_threshold": 7.0}},
    ],
)
def test_malformed_recorded_controls_are_rejected(controls: object) -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    saved = _saved(runtime)
    saved["runtime_provenance"]["session_controls"] = controls

    with pytest.raises(CheckpointError):
        OrganismRuntime.from_checkpoint(saved, **RUNTIME_KWARGS)
