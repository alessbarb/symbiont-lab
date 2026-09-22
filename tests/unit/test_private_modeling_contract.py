from __future__ import annotations

import hashlib

import pytest

from symbiont.modeling import (
    ArchitectureId,
    ModelArtifactManifest,
    ModelInferenceResult,
    ModelObjective,
    ModelRegistry,
    ModelState,
    ModelTrainingAuthority,
    NativeTokenizer,
    PrivateModelBridge,
    TokenPrediction,
    TrainingBudget,
    TrainingRequest,
)
from symbiont.modeling.experience import EpistemicStatus, ExperienceRecord, SourceKind


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _request(*, organism_id: str = "organism-a") -> TrainingRequest:
    return TrainingRequest(
        organism_id=organism_id,
        corpus_hash=HASH_A,
        tokenizer_hash=HASH_B,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=7,
        context_window=64,
        requested_parameters=2_000_000,
        requested_epochs=8,
        requested_steps=500,
        created_tick_class=20,
    )


def _artifact(*, organism_id: str = "organism-a") -> ModelArtifactManifest:
    return ModelArtifactManifest.build(
        request=_request(organism_id=organism_id),
        parameter_count=100_000,
        weights_hash=HASH_C,
        artifact_bytes=1024,
    )


def _record(record_id: str = "r1") -> ExperienceRecord:
    return ExperienceRecord(
        record_id=record_id,
        organism_id="organism-a",
        tick_class=1,
        context_tokens=("sense.1", "state.2"),
        action_token="action.observe",
        outcome_tokens=("outcome.stable",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=("evidence.1",),
        confidence_class=5,
        source_kind=SourceKind.DIRECT,
    )


def test_authority_rejects_parameter_budget_escape():
    authority = ModelTrainingAuthority(TrainingBudget(max_parameters=50_000))
    with pytest.raises(ValueError, match="parameter"):
        authority.authorize(_request(), corpus_records=8)


def test_registry_activation_requires_independent_authorization():
    registry = ModelRegistry("organism-a")
    record = registry.register(_artifact())
    assert record.state is ModelState.CANDIDATE
    registry.transition(record.model_id, ModelState.SHADOW)
    with pytest.raises(ValueError, match="promotion"):
        registry.transition(record.model_id, ModelState.ACTIVE)
    active = registry.transition(
        record.model_id,
        ModelState.ACTIVE,
        promotion_authorized=True,
        evaluation_summary=(1, 2),
    )
    assert active.state is ModelState.ACTIVE
    assert registry.active == active


def test_registry_checkpoint_is_organism_private_and_restorable():
    registry = ModelRegistry("organism-a")
    record = registry.register(_artifact())
    registry.transition(record.model_id, ModelState.SHADOW)
    restored = ModelRegistry.restore(registry.checkpoint(), organism_id="organism-a")
    assert restored.get(record.model_id) == registry.get(record.model_id)
    with pytest.raises(ValueError, match="mismatch"):
        ModelRegistry.restore(registry.checkpoint(), organism_id="organism-b")


def test_private_bridge_keeps_shadow_inference_explicit():
    tokenizer = NativeTokenizer.from_records((_record(),))
    request = _request()
    artifact = ModelArtifactManifest.build(
        request=TrainingRequest(
            organism_id=request.organism_id,
            corpus_hash=request.corpus_hash,
            tokenizer_hash=tokenizer.tokenizer_hash,
            architecture_id=request.architecture_id,
            objective=request.objective,
            seed=request.seed,
            context_window=request.context_window,
            requested_parameters=request.requested_parameters,
            requested_epochs=request.requested_epochs,
            requested_steps=request.requested_steps,
            created_tick_class=request.created_tick_class,
        ),
        parameter_count=10_000,
        weights_hash=HASH_C,
        artifact_bytes=1024,
    )
    registry = ModelRegistry("organism-a")
    record = registry.register(artifact)
    registry.transition(record.model_id, ModelState.SHADOW)

    class Gateway:
        def infer(self, *, model_id, token_ids, top_k=4):
            target = tokenizer.token_to_id["outcome.stable"]
            return ModelInferenceResult(model_id, (TokenPrediction(target, 0.75),))

    bridge = PrivateModelBridge(registry=registry, tokenizer=tokenizer, gateway=Gateway())
    with pytest.raises(ValueError, match="eligible"):
        bridge.predict(("sense.1",), model_id=record.model_id)
    proposal = bridge.predict(("sense.1",), model_id=record.model_id, allow_shadow=True)
    assert proposal.predicted_token == "outcome.stable"
    assert proposal.model_id == record.model_id


def test_active_private_counterfactual_is_non_mutating_and_active_only():
    from types import SimpleNamespace

    from symbiont.modeling import ModeledOrganismRuntime
    from symbiont.modeling.proposals import ModelPredictionProposal

    runtime = ModeledOrganismRuntime(organism_id="counterfactual-runtime")
    runtime._model_registry = SimpleNamespace(
        active=SimpleNamespace(model_id="model.active")
    )

    class Bridge:
        def __init__(self):
            self.calls = []

        def predict(
            self,
            context_tokens,
            *,
            model_id,
            target_token,
            allow_shadow,
        ):
            self.calls.append(
                (tuple(context_tokens), model_id, target_token, allow_shadow)
            )
            return ModelPredictionProposal(
                target_token=target_token,
                horizon_class=1,
                predicted_token="outcome.opaque",
                confidence_class=6,
                model_id=model_id,
            )

    bridge = Bridge()
    runtime._private_model_bridge = bridge
    before = runtime.experience_ledger.records

    proposal = runtime.active_private_counterfactual(
        ("sense.opaque", "state.sense.opaque.level.4"),
        action_token="action.primitive.deadbeef",
    )

    assert proposal.predicted_token == "outcome.opaque"
    assert runtime.experience_ledger.records == before
    assert bridge.calls
    prefix, model_id, target_token, allow_shadow = bridge.calls[0]
    assert model_id == "model.active"
    assert target_token == "<OUTCOME>"
    assert allow_shadow is False
    assert "action.primitive.deadbeef" in prefix
