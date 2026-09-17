from __future__ import annotations

import pytest

pytest.importorskip("torch")

from symbiont.modeling import (
    ArchitectureId,
    EpistemicStatus,
    ExperienceRecord,
    ModelObjective,
    ModelTrainingAuthority,
    NativeTokenizer,
    SourceKind,
    TrainingBudget,
    TrainingRequest,
    build_training_corpus,
)
from symbiont_lab.modeling import (
    FileArtifactStore,
    PromotionPolicy,
    TrainingConfig,
    encode_corpus,
    evaluate_candidate,
    train_private_model,
)
from symbiont_lab.modeling.gateway import ArtifactInferenceGateway


def _records() -> tuple[ExperienceRecord, ...]:
    records = []
    for tick in range(48):
        phase = tick % 3
        records.append(ExperienceRecord(
            record_id=f"r{tick}",
            organism_id="organism-training",
            tick_class=tick,
            context_tokens=(f"sense.{phase}", "state.stable"),
            action_token="action.observe",
            outcome_tokens=(f"outcome.{phase}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.{tick}",),
            confidence_class=6,
            source_kind=SourceKind.DIRECT,
        ))
    return tuple(records)


def test_real_gru_candidate_is_hash_bound_and_inferable(tmp_path):
    corpus = build_training_corpus(_records())
    tokenizer = NativeTokenizer.from_records(corpus.train)
    encoded = encode_corpus(corpus, tokenizer, context_window=32)
    request = TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=7,
        context_window=32,
        requested_parameters=5_000_000,
        requested_epochs=2,
        requested_steps=8,
        created_tick_class=corpus.manifest.last_tick_class,
    )
    result = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=8)),
        config=TrainingConfig(batch_size=8, patience=2),
    )
    assert result.artifact.manifest.parameter_count > 1000
    assert result.steps_completed <= 8
    evaluation, decision = evaluate_candidate(
        result.artifact,
        encoded,
        policy=PromotionPolicy(minimum_log_loss_gain=0.0),
    )
    assert evaluation.candidate.predictions > 0

    store = FileArtifactStore(tmp_path)
    store.put(result.artifact)
    restored = store.get(result.artifact.manifest.model_id)
    assert restored.manifest == result.artifact.manifest
    gateway = ArtifactInferenceGateway(store, vocab_size=encoded.vocab_size, pad_id=encoded.pad_id)
    inference = gateway.infer(
        model_id=result.artifact.manifest.model_id,
        token_ids=encoded.test.sequences[0][:-1],
        top_k=3,
    )
    assert inference.model_id == result.artifact.manifest.model_id
    assert len(inference.predictions) == 3
