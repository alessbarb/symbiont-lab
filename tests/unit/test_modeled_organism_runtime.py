from __future__ import annotations

from symbiont.modeling import (
    ArchitectureId,
    ModelArtifactManifest,
    ModelObjective,
    ModelState,
    ModeledOrganismRuntime,
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
