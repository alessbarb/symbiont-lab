from __future__ import annotations

import json
from importlib import resources
from dataclasses import replace

from symbiont.cognition.genome import GenomeCodec
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.modeling import (
    ArchitectureId,
    ExperienceRecord,
    EpistemicStatus,
    ModelArtifactManifest,
    ModelObjective,
    ModelState,
    ModeledOrganismRuntime,
    SourceKind,
    TrainingRequest,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _artifact(runtime: ModeledOrganismRuntime) -> ModelArtifactManifest:
    request = TrainingRequest(
        organism_id=runtime.organism_id,
        corpus_hash=HASH_A,
        tokenizer_hash=HASH_B,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=7,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=100,
        created_tick_class=0,
    )
    return ModelArtifactManifest.build(
        request=request,
        parameter_count=100_000,
        weights_hash=HASH_C,
        artifact_bytes=1024,
    )


def test_modeled_runtime_restores_registry_without_weights_or_bridge():
    runtime = ModeledOrganismRuntime(organism_id="modeled-a")
    artifact = _artifact(runtime)
    shadow = runtime.adopt_private_model(artifact, evaluation_summary=(0, 1))
    assert shadow.state is ModelState.SHADOW
    active = runtime.activate_private_model(
        shadow.model_id,
        promotion_authorized=True,
        evaluation_summary=(1, 2),
    )
    assert active.state is ModelState.ACTIVE

    checkpoint = runtime.checkpoint()
    assert "private_model_registry" in checkpoint
    assert "weights" not in str(checkpoint).lower()
    restored = ModeledOrganismRuntime.from_checkpoint(checkpoint)
    assert restored.organism_id == runtime.organism_id
    assert restored.model_registry.active is not None
    assert restored.model_registry.active.model_id == active.model_id
    assert restored._private_model_bridge is None


def test_training_request_is_organism_owned_and_charged():
    runtime = ModeledOrganismRuntime(organism_id="modeled-request")
    before = runtime.metabolism.snapshot().reserve["cognition"]
    request = runtime.request_private_model_training(
        corpus_hash=HASH_A,
        tokenizer_hash=HASH_B,
        architecture_id=ArchitectureId.TRANSFORMER_V1,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=100,
        seed=11,
    )
    after = runtime.metabolism.snapshot().reserve["cognition"]
    assert request.organism_id == runtime.organism_id
    assert after < before


def test_clonal_child_inherits_modeling_capacity_but_not_private_model_or_experience():
    payload = json.loads(
        resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text()
    )
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="model-inheritance", capacity=2)
    parent = ModeledOrganismRuntime(
        organism_id="model-parent",
        genome=genome,
        birth_authority=authority,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    parent.adopt_private_model(_artifact(parent))
    parent.record_experience(ExperienceRecord(
        record_id="parent.experience",
        organism_id=parent.organism_id,
        tick_class=0,
        context_tokens=("sense.parent",),
        action_token=None,
        outcome_tokens=("outcome.parent",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=("evidence.parent",),
        confidence_class=7,
        source_kind=SourceKind.DIRECT,
    ))
    parent.living_body_state.growth_progress = 1.0
    child = parent.materialize_clonal_bud()
    assert isinstance(child, ModeledOrganismRuntime)
    assert child is not None
    assert child.model_registry.records == ()
    assert child.experience_ledger.records == ()



def _transition(runtime: ModeledOrganismRuntime, tick: int) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=f"transition.test.{tick}",
        organism_id=runtime.organism_id,
        tick_class=tick,
        context_tokens=(f"sense.test.{tick % 4}",),
        action_token=f"action.test.{tick % 3}",
        outcome_tokens=(f"outcome.test.{(tick + 1) % 5}",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"evidence.test.{tick}",),
        confidence_class=7,
        source_kind=SourceKind.ACTION_OUTCOME,
    )


def test_autonomous_private_learning_waits_for_causal_experience():
    runtime = ModeledOrganismRuntime(organism_id="learning-demand")
    for tick in range(63):
        runtime.record_experience(_transition(runtime, tick))

    assert runtime.autonomous_private_learning_plan() is None

    runtime.record_experience(_transition(runtime, 63))
    before = runtime.metabolism.snapshot().reserve["cognition"]
    plan = runtime.autonomous_private_learning_plan()
    after = runtime.metabolism.snapshot().reserve["cognition"]

    assert plan is not None
    assert plan.reason == "bootstrap-experience"
    assert plan.transition_count == 64
    assert plan.new_transition_count == 64
    assert plan.request.organism_id == runtime.organism_id
    assert plan.request.corpus_hash == plan.corpus.manifest.corpus_hash
    assert plan.request.tokenizer_hash == plan.tokenizer.tokenizer_hash
    assert after < before


def test_autonomous_private_learning_does_not_repeat_same_experience():
    runtime = ModeledOrganismRuntime(organism_id="learning-no-repeat")
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))

    first = runtime.autonomous_private_learning_plan()
    assert first is not None
    reserve_after_first = runtime.metabolism.snapshot().reserve["cognition"]

    assert runtime.autonomous_private_learning_plan() is None
    assert runtime.metabolism.snapshot().reserve["cognition"] == reserve_after_first


def test_autonomous_private_learning_state_survives_checkpoint():
    runtime = ModeledOrganismRuntime(organism_id="learning-checkpoint")
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    plan = runtime.autonomous_private_learning_plan()
    assert plan is not None

    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint())

    assert restored._private_learning_last_transition_tick == 63
    assert restored._private_learning_last_corpus_hash == plan.corpus.manifest.corpus_hash
    assert restored.autonomous_private_learning_plan() is None



def test_autonomous_private_learning_reacts_to_own_model_contradictions():
    runtime = ModeledOrganismRuntime(organism_id="learning-revision")
    shadow = runtime.adopt_private_model(_artifact(runtime), evaluation_summary=(1, 2))
    runtime.activate_private_model(
        shadow.model_id,
        promotion_authorized=True,
        evaluation_summary=(1, 2),
    )

    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))

    # Existing active model means historical experience is not automatically
    # replayed as a fresh bootstrap demand.
    runtime._private_learning_new_transition_count = 0
    runtime._private_learning_last_transition_tick = 63

    for tick in range(64, 96):
        runtime.record_experience(_transition(runtime, tick))

    for index in range(8):
        runtime.record_experience(ExperienceRecord(
            record_id=f"validation.test.{index}",
            organism_id=runtime.organism_id,
            tick_class=95 + index,
            context_tokens=("model.context",),
            action_token=None,
            outcome_tokens=("model.outcome",),
            epistemic_status=EpistemicStatus.CONTRADICTED,
            evidence_refs=(f"evidence.validation.{index}",),
            confidence_class=4,
            source_kind=SourceKind.MODEL,
        ))

    plan = runtime.autonomous_private_learning_plan()

    assert plan is not None
    assert plan.reason == "prediction-revision"
    assert plan.new_transition_count == 32
    assert plan.contradiction_ratio == 1.0



def test_autonomous_replay_budget_grows_with_learning_pressure():
    bootstrap = ModeledOrganismRuntime(organism_id="replay-pressure-bootstrap")
    for tick in range(64):
        bootstrap.record_experience(_transition(bootstrap, tick))
    bootstrap_plan = bootstrap.autonomous_private_learning_plan()
    assert bootstrap_plan is not None

    revision = ModeledOrganismRuntime(organism_id="replay-pressure-revision")
    shadow = revision.adopt_private_model(_artifact(revision), evaluation_summary=(1, 2))
    revision.activate_private_model(
        shadow.model_id,
        promotion_authorized=True,
        evaluation_summary=(1, 2),
    )
    for tick in range(96):
        revision.record_experience(_transition(revision, tick))
    revision._private_learning_last_transition_tick = -1
    revision._private_learning_new_transition_count = 96
    for index in range(8):
        revision.record_experience(ExperienceRecord(
            record_id=f"validation.pressure.{index}",
            organism_id=revision.organism_id,
            tick_class=96 + index,
            context_tokens=("model.context",),
            action_token=None,
            outcome_tokens=("model.outcome",),
            epistemic_status=EpistemicStatus.CONTRADICTED,
            evidence_refs=(f"evidence.pressure.{index}",),
            confidence_class=4,
            source_kind=SourceKind.MODEL,
        ))
    revision_plan = revision.autonomous_private_learning_plan()
    assert revision_plan is not None

    assert 0.0 <= bootstrap_plan.replay_pressure <= 1.0
    assert revision_plan.replay_pressure == 1.0
    assert revision_plan.request.requested_epochs > bootstrap_plan.request.requested_epochs
    assert revision_plan.request.requested_steps > bootstrap_plan.request.requested_steps


def test_autonomous_replay_budget_is_bounded():
    runtime = ModeledOrganismRuntime(organism_id="replay-pressure-bounded")
    for tick in range(256):
        runtime.record_experience(_transition(runtime, tick))

    plan = runtime.autonomous_private_learning_plan()
    assert plan is not None
    assert plan.replay_pressure == 1.0
    assert plan.request.requested_epochs == 8
    assert plan.request.requested_steps == 48



def test_autonomous_private_learning_plan_authors_stopping_policy():
    runtime = ModeledOrganismRuntime(organism_id="autonomous-stopping-plan")
    for tick in range(128):
        runtime.record_experience(_transition(runtime, tick))

    plan = runtime.autonomous_private_learning_plan()

    assert plan is not None
    assert plan.request.autonomous_stopping is True
    assert plan.request.requested_patience == 2
    assert plan.request.requested_min_validation_gain == 0.005


def test_training_request_identity_includes_stopping_policy():
    runtime = ModeledOrganismRuntime(organism_id="stopping-request-id")
    base = runtime.request_private_model_training(
        corpus_hash=HASH_A,
        tokenizer_hash=HASH_B,
        architecture_id=ArchitectureId.GRU_V1,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=24,
        seed=7,
    )
    autonomous = runtime.request_private_model_training(
        corpus_hash=HASH_A,
        tokenizer_hash=HASH_B,
        architecture_id=ArchitectureId.GRU_V1,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=24,
        seed=7,
        autonomous_stopping=True,
        requested_patience=2,
        requested_min_validation_gain=0.005,
    )

    assert base.request_id != autonomous.request_id
