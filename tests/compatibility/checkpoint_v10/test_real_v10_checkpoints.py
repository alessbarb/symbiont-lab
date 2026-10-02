"""Real schema-10 checkpoints through restore and every authorized transform."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.core.orchestration.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import (
    IDENTITY_SCOPE,
    CheckpointError,
    verify_checkpoint_identity,
)
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont_lab.physics3d.reembodiment import (
    PhysicsEmbodimentDescriptor,
    migrate_temporal_domains,
    prepare_fresh_embodiment_checkpoint,
)
from symbiont_lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)

FIXTURES = Path(__file__).parent
PLAIN_KWARGS = dict(bootstrap_semantic_senses=False, discover_senses=False, min_samples=1)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _embodied_kwargs(body: CausalBody) -> dict:
    return dict(
        host_lifecycle=subject_lifecycle(body),
        host_reading_providers=(body,),
        kernel_limits=KernelLimits(),
        actuator_constitution_override=body.surface,
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
        interoception_mode="absent",
    )


@pytest.mark.parametrize(
    "name", ["genomeless_runtime", "private_model_runtime", "embodied_private_model_runtime"]
)
def test_fixture_is_a_real_schema_10_payload(name: str) -> None:
    payload = _load(name)

    assert payload["schema_version"] == 10
    assert payload["runtime_provenance"]["checkpoint_schema_version"] == 10
    assert "identity_scope" not in payload["checkpoint_lineage"]
    assert "session_controls" not in payload["runtime_provenance"]
    verify_checkpoint_identity(payload)  # legacy identifier: accepted unverified


@pytest.mark.parametrize(
    ("name", "runtime_type"),
    [
        ("genomeless_runtime", OrganismRuntime),
        ("private_model_runtime", PrivateModelOrganismRuntime),
    ],
)
def test_real_v10_checkpoint_restores_and_its_next_save_is_verifiable(name, runtime_type) -> None:
    legacy = _load(name)

    restored = runtime_type.from_checkpoint(legacy, **PLAIN_KWARGS)
    saved = json.loads(json.dumps(restored.checkpoint()))

    assert restored.organism_id == legacy["organism_id"]
    assert restored.tick_count == legacy["saved_at_tick"]
    assert saved["schema_version"] == 11
    assert saved["checkpoint_lineage"]["identity_scope"] == IDENTITY_SCOPE
    assert (
        saved["checkpoint_lineage"]["parent_checkpoint_hash"]
        == (legacy["checkpoint_lineage"]["checkpoint_id"])
    )
    runtime_type.from_checkpoint(saved, **PLAIN_KWARGS)


def test_real_v10_genomeless_resident_adopts_canonical_cognition() -> None:
    legacy = _load("genomeless_runtime")
    assert legacy["genome"] is None

    restored = restore_resident_with_canonical_cognition(legacy, **PLAIN_KWARGS)

    assert restored.tick_count == legacy["saved_at_tick"]
    assert restored.genome is not None and restored.cognitive_bridge is not None


def test_real_v10_symbiont_can_be_reembodied() -> None:
    legacy = _load("embodied_private_model_runtime")
    body = CausalBody(actuator_count=3, seed=311)
    fresh = json.loads(
        json.dumps(
            build_subject(
                body,
                organism_id=legacy["organism_id"],
                runtime_class=PrivateModelOrganismRuntime,
                factorized_effects=True,
            ).checkpoint()
        )
    )

    transformed = prepare_fresh_embodiment_checkpoint(
        legacy,
        fresh,
        contract=PhysicsEmbodimentDescriptor(
            body_kind="causal-body-b", receptor_count=3, effector_count=3
        ),
        canonical_contract_fingerprint=body.surface.contract_fingerprint,
    )
    restored = PrivateModelOrganismRuntime.from_checkpoint(
        json.loads(json.dumps(transformed)), **_embodied_kwargs(body)
    )

    lineage = transformed["checkpoint_lineage"]
    assert lineage["transforms"] == ["re-embodiment"]
    assert lineage["parent_checkpoint_hash"] == legacy["checkpoint_lineage"]["checkpoint_id"]
    assert restored.organism_id == legacy["organism_id"]
    assert restored.tick_count == legacy["saved_at_tick"]
    assert transformed["experience_ledger"] == legacy["experience_ledger"]
    assert transformed["cognitive_bridge"] == legacy["cognitive_bridge"]


def test_real_v10_checkpoint_survives_temporal_decontamination_then_reembodiment() -> None:
    legacy = _load("embodied_private_model_runtime")
    saved_tick = legacy["saved_at_tick"]
    legacy["living_body"]["age_ticks"] = saved_tick  # Body age written from the global tick
    legacy["embodiment_lifecycle"] = {
        "schema_version": 1,
        "state": "dormant",
        "epoch": 2,
        "current": {
            "body_kind": "causal-body-a",
            "receptor_count": 2,
            "effector_count": 2,
            "started_tick": saved_tick - 4,
        },
        "history": [],
    }

    decontaminated = migrate_temporal_domains(legacy)

    assert decontaminated["living_body"]["age_ticks"] == 4
    assert decontaminated["checkpoint_lineage"]["transforms"] == ["temporal-decontamination"]
    body = CausalBody(actuator_count=2, seed=127)
    PrivateModelOrganismRuntime.from_checkpoint(
        json.loads(json.dumps(decontaminated)), **_embodied_kwargs(body)
    )


def test_a_transformed_legacy_checkpoint_is_still_identity_protected() -> None:
    legacy = _load("genomeless_runtime")
    body_free = restore_resident_with_canonical_cognition(legacy, **PLAIN_KWARGS).checkpoint()
    body_free["generation"] += 1

    with pytest.raises(CheckpointError, match="does not match its recorded checkpoint_id"):
        OrganismRuntime.from_checkpoint(body_free, **PLAIN_KWARGS)
