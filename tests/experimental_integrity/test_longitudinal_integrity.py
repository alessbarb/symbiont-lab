"""Longitudinal Integrity v1 §14, experimental-integrity tier.

A restart must not be a way for the apparatus to change the organism or the
condition it is being studied under.
"""

from __future__ import annotations

import inspect
import json

import pytest
from tests.checkpoints import edited

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.social.relations import RelationLedger
from symbiont.host.checkpoint import CheckpointError
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

RUNTIME_KWARGS = dict(
    bootstrap_semantic_senses=False, discover_senses=False, min_samples=1, investigate_ticks=0
)


def _developed(runtime_type=PrivateModelOrganismRuntime):
    runtime = runtime_type(organism_id="integrity-subject", **RUNTIME_KWARGS)
    runtime.run(12)
    return runtime


def _restart(runtime, **kwargs):
    payload = json.loads(json.dumps(runtime.checkpoint()))
    return type(runtime).from_checkpoint(payload, **RUNTIME_KWARGS, **kwargs)


def test_observer_density_does_not_change_the_continuity_outcome() -> None:
    quiet = _developed()
    observed = _developed()
    for _ in range(8):
        observed.checkpoint(advance_lineage=False)
        observed.state_hash()

    quiet_after = _restart(quiet)
    observed_after = _restart(observed)
    quiet_after.run(6)
    observed_after.run(6)

    assert observed_after.state_hash() == quiet_after.state_hash()


@pytest.mark.parametrize(
    ("setter", "attribute"),
    [
        ("set_cognitive_plasticity_enabled", "_cognitive_plasticity_enabled"),
        ("set_predictor_promotion_enabled", "_predictor_promotion_enabled"),
    ],
)
def test_restart_does_not_silently_toggle_a_governed_learning_condition(
    setter: str, attribute: str
) -> None:
    runtime = _developed()
    getattr(runtime, setter)(False)

    restored = _restart(runtime)

    assert getattr(restored, attribute) is False
    assert restored.checkpoint()["runtime_provenance"]["changed_since_restore"] == []


def test_restore_takes_no_evaluator_or_world_input() -> None:
    for runtime_type in (OrganismRuntime, PrivateModelOrganismRuntime):
        parameters = inspect.signature(runtime_type.from_checkpoint).parameters
        assert set(parameters) == {"payload", "kwargs"}
        assert not any(
            word in name.lower()
            for name in inspect.signature(runtime_type.__init__).parameters
            for word in ("evaluator", "ground_truth", "world")
        )


def test_missing_organism_state_cannot_be_supplied_from_outside_the_checkpoint() -> None:
    runtime = _developed(OrganismRuntime)
    payload = json.loads(json.dumps(runtime.checkpoint()))
    del payload["social_ledger"]

    with pytest.raises(CheckpointError, match="missing required field 'social_ledger'"):
        OrganismRuntime.from_checkpoint(
            edited(payload), **RUNTIME_KWARGS, social_ledger=RelationLedger()
        )
