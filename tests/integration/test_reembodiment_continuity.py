"""Longitudinal Integrity v1 §12: re-embodiment continuity.

Mechanical continuity only: the Symbiont's own state survives a Body
replacement and current-Body authority is withdrawn. Nothing here measures
whether the retained knowledge is useful in the new Body.
"""

from __future__ import annotations

import json

import pytest

from symbiont.actuation.binding import BindingStatus
from symbiont.cognition.limits import KernelLimits
from symbiont.host.checkpoint import CheckpointError
from symbiont.host.continuity import REGISTER, Reembodiment
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont_lab.physics3d.reembodiment import (
    PhysicsEmbodimentDescriptor,
    prepare_fresh_embodiment_checkpoint,
)
from symbiont_lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    run_ticks,
    subject_lifecycle,
)

ORGANISM_ID = "reembodied-subject"
DEVELOPMENT_TICKS = 600
SAVE_METADATA = {"checkpoint_lineage", "runtime_provenance"}
# Body-owned state the transform takes from the fresh Body.
FRESH_BODY_FIELDS = {
    "living_body",
    "metabolism",
    "homeostasis",
    "physiology",
    "pending_embodied_work",
    "resting_requested",
}


def _subject(body: CausalBody) -> PrivateModelOrganismRuntime:
    return build_subject(
        body,
        organism_id=ORGANISM_ID,
        runtime_class=PrivateModelOrganismRuntime,
        factorized_effects=True,
    )


def _json(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def _competence_ids(runtime: PrivateModelOrganismRuntime) -> set[str]:
    return {item.competence_id for item in runtime._action_domain.competence_library.items}


class _Case:
    """Body A developed, then the same Symbiont moved into a fresh Body B."""

    def __init__(self) -> None:
        body_a = CausalBody(actuator_count=4, seed=127)
        developed = _subject(body_a)
        run_ticks(developed, body_a, DEVELOPMENT_TICKS)
        domain = developed._action_domain
        self.body_a_fingerprint = body_a.surface.contract_fingerprint
        self.valid_bindings_in_a = sum(
            binding.status is BindingStatus.VALID for binding in domain.execution_bindings.items
        )
        self.competences_in_a = _competence_ids(developed)
        self.graph_nodes_in_a = {node.node_id for node in developed.cognitive_bridge.graph.nodes}
        self.experience_in_a = [r.record_id for r in developed.experience_ledger.records]
        self.previous = _json(developed.checkpoint())
        del developed

        self.body_b = CausalBody(actuator_count=6, seed=311)
        self.fresh = _json(_subject(self.body_b).checkpoint())
        self.transformed = prepare_fresh_embodiment_checkpoint(
            self.previous,
            self.fresh,
            contract=PhysicsEmbodimentDescriptor(
                body_kind="causal-body-b", receptor_count=6, effector_count=6
            ),
            canonical_contract_fingerprint=self.body_b.surface.contract_fingerprint,
        )

    def restore(self, payload: dict | None = None) -> PrivateModelOrganismRuntime:
        return PrivateModelOrganismRuntime.from_checkpoint(
            _json(self.transformed if payload is None else payload),
            host_lifecycle=subject_lifecycle(self.body_b),
            host_reading_providers=(self.body_b,),
            kernel_limits=KernelLimits(),
            actuator_constitution_override=self.body_b.surface,
            bootstrap_semantic_senses=False,
            discover_senses=True,
            min_samples=1,
            interoception_mode="absent",
        )


@pytest.fixture(scope="module")
def case() -> _Case:
    return _Case()


def test_body_a_development_is_not_trivial(case: _Case) -> None:
    assert case.previous["saved_at_tick"] == DEVELOPMENT_TICKS
    assert case.valid_bindings_in_a >= 1
    assert case.competences_in_a
    assert case.graph_nodes_in_a
    assert case.experience_in_a


def test_symbiont_owned_state_is_preserved_exactly(case: _Case) -> None:
    preserved = {
        field
        for entry in REGISTER
        if entry.reembodiment is Reembodiment.PRESERVED
        for field in entry.checkpoint_fields
    } - SAVE_METADATA

    changed = {
        field
        for field in preserved
        if field in case.previous and case.transformed.get(field) != case.previous[field]
    }

    # last_runtime_vital_state shares its owner with preserved chronology but is
    # a Body fact: a fresh Body always starts active.
    assert changed <= {"last_runtime_vital_state"}
    assert len(preserved & set(case.previous)) > 40


def test_body_owned_state_comes_from_the_fresh_body(case: _Case) -> None:
    for field in sorted(FRESH_BODY_FIELDS):
        assert case.transformed[field] == case.fresh[field], field
    assert case.transformed["last_runtime_vital_state"] == "active"


def test_identity_and_time_continue_and_the_transform_is_recorded(case: _Case) -> None:
    lineage = case.transformed["checkpoint_lineage"]

    assert case.transformed["organism_id"] == ORGANISM_ID
    assert case.transformed["saved_at_tick"] == DEVELOPMENT_TICKS
    assert lineage["transforms"] == ["re-embodiment"]
    assert lineage["parent_checkpoint_hash"] == case.previous["checkpoint_lineage"]["checkpoint_id"]

    restored = case.restore()
    assert restored.organism_id == ORGANISM_ID
    assert restored.tick_count == DEVELOPMENT_TICKS


def test_current_body_authority_is_withdrawn(case: _Case) -> None:
    restored = case.restore()
    domain = restored._action_domain

    assert domain.surface.contract_fingerprint == case.body_b.surface.contract_fingerprint
    assert domain.surface.contract_fingerprint != case.body_a_fingerprint
    assert not any(
        binding.status is BindingStatus.VALID for binding in domain.execution_bindings.items
    )
    assert domain.active_commitment is None
    assert "embodiment_episode" not in case.transformed

    lifecycle = case.transformed["embodiment_lifecycle"]
    assert lifecycle["epoch"] == 2
    assert lifecycle["current"]["started_tick"] == DEVELOPMENT_TICKS
    assert lifecycle["current"]["contract_fingerprint"] == (
        case.body_b.surface.contract_fingerprint
    )
    assert [entry["ended_tick"] for entry in lifecycle["history"]] == [DEVELOPMENT_TICKS]


def test_knowledge_survives_as_knowledge_without_authority(case: _Case) -> None:
    restored = case.restore()

    assert {node.node_id for node in restored.cognitive_bridge.graph.nodes} == (
        case.graph_nodes_in_a
    )
    assert [r.record_id for r in restored.experience_ledger.records] == case.experience_in_a
    assert _competence_ids(restored) >= case.competences_in_a


def test_experience_continues_in_body_b_without_erasing_body_a_knowledge(
    case: _Case,
) -> None:
    # A Body of its own: the module fixture's Body B must stay untouched.
    body_b = CausalBody(actuator_count=6, seed=311)
    restored = PrivateModelOrganismRuntime.from_checkpoint(
        _json(case.transformed),
        host_lifecycle=subject_lifecycle(body_b),
        host_reading_providers=(body_b,),
        kernel_limits=KernelLimits(),
        actuator_constitution_override=body_b.surface,
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
        interoception_mode="absent",
    )

    run_ticks(restored, body_b, 50)

    assert restored.tick_count == DEVELOPMENT_TICKS + 50
    assert len(restored.experience_ledger.records) > len(case.experience_in_a)
    recorded = {record.record_id for record in restored.experience_ledger.records}
    retained = recorded | {record.record_id for record in restored.experience_archive.records}
    assert set(case.experience_in_a) <= retained
    assert _competence_ids(restored) >= case.competences_in_a


def test_a_modified_reembodied_checkpoint_is_rejected(case: _Case) -> None:
    tampered = dict(case.transformed)
    tampered["generation"] = case.transformed["generation"] + 1

    with pytest.raises(CheckpointError, match="does not match its recorded checkpoint_id"):
        case.restore(tampered)
