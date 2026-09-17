from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from symbiont.modeling import (  # noqa: E402
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
from symbiont_lab.modeling import (  # noqa: E402
    FileArtifactStore,
    TrainingConfig,
    adapt_private_model,
    encode_corpus,
    train_private_model,
)
from symbiont_lab.modeling.gateway import load_artifact_model  # noqa: E402


def _records(organism: str, *, flipped: bool = False) -> tuple[ExperienceRecord, ...]:
    rows = []
    for tick in range(36):
        phase = tick % 3
        outcome = (phase + (1 if flipped else 0)) % 3
        rows.append(ExperienceRecord(
            record_id=f"{organism}-{flipped}-{tick}",
            organism_id=organism,
            tick_class=tick,
            context_tokens=(f"sense.{phase}", "state.stable"),
            action_token="action.observe",
            outcome_tokens=(f"outcome.{outcome}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.{tick}",),
            confidence_class=6,
            source_kind=SourceKind.DIRECT,
        ))
    return tuple(rows)


def _request(corpus, tokenizer, *, seed: int, parent: str | None = None,
             architecture: ArchitectureId = ArchitectureId.GRU_V1,
             tokenizer_hash: str | None = None, reason: str | None = None) -> TrainingRequest:
    return TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer_hash or tokenizer.tokenizer_hash,
        architecture_id=architecture,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=32,
        requested_parameters=5_000_000,
        requested_epochs=2,
        requested_steps=6,
        created_tick_class=corpus.manifest.last_tick_class,
        parent_model_id=parent,
        adaptation_reason=reason,
    )


def _train_parent(tmp_path):
    records = _records("organism-adapt")
    corpus = build_training_corpus(records)
    tokenizer = NativeTokenizer.from_records(corpus.train)
    encoded = encode_corpus(corpus, tokenizer, context_window=32)
    result = train_private_model(
        request=_request(corpus, tokenizer, seed=101),
        corpus=encoded,
        authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=6)),
        config=TrainingConfig(batch_size=8, patience=2),
    )
    store = FileArtifactStore(tmp_path)
    store.put(result.artifact)
    return result, corpus, tokenizer, store


def test_adaptation_loads_parent_weights_and_records_real_lineage(tmp_path):
    parent_result, parent_corpus, tokenizer, store = _train_parent(tmp_path)
    post_corpus = build_training_corpus(_records("organism-adapt", flipped=True))
    encoded = encode_corpus(post_corpus, tokenizer, context_window=32)
    request = _request(
        post_corpus, tokenizer, seed=101, parent=parent_result.artifact.manifest.model_id,
        reason="post-shift direct evidence",
    )
    adapted = adapt_private_model(
        request=request,
        corpus=encoded,
        parent_artifact=store.get(request.parent_model_id),
        authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=6)),
        config=TrainingConfig(batch_size=8, patience=2),
    )
    parent = parent_result.artifact
    successor = adapted.artifact
    assert successor.weights != parent.weights
    assert successor.manifest.parent_model_id == parent.manifest.model_id
    assert successor.manifest.ancestor_model_id == parent.manifest.model_id
    assert successor.manifest.generation == 1
    assert successor.manifest.adaptation_reason == "post-shift direct evidence"
    assert successor.manifest.adaptation_cost_steps > 0
    assert successor.manifest.authorized_step_ceiling == 6
    parent_model = load_artifact_model(parent, vocab_size=encoded.vocab_size, pad_id=encoded.pad_id)
    successor_model = load_artifact_model(successor, vocab_size=encoded.vocab_size, pad_id=encoded.pad_id)
    sample = torch.tensor([encoded.test.sequences[0][:-1]], dtype=torch.long)
    with torch.no_grad():
        expected = parent_model(sample, attention_mask=torch.ones_like(sample, dtype=torch.bool))
        actual = successor_model(sample, attention_mask=torch.ones_like(sample, dtype=torch.bool))
    assert expected.shape == actual.shape
    assert not torch.equal(expected, actual)


def test_adaptation_rejects_cross_organism_architecture_and_tokenizer(tmp_path):
    parent_result, _, tokenizer, store = _train_parent(tmp_path)
    foreign = build_training_corpus(_records("organism-foreign"))
    foreign_tokenizer = NativeTokenizer.from_records(foreign.train)
    encoded = encode_corpus(foreign, foreign_tokenizer, context_window=32)
    request = _request(
        foreign, foreign_tokenizer, seed=101, parent=parent_result.artifact.manifest.model_id,
        reason="invalid",
    )
    with pytest.raises(ValueError, match="different organism"):
        adapt_private_model(
            request=request, corpus=encoded, parent_artifact=store.get(request.parent_model_id),
            authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=6)),
        )

    own = build_training_corpus(_records("organism-adapt", flipped=True))
    own_encoded = encode_corpus(own, tokenizer, context_window=32)
    bad_arch = _request(own, tokenizer, seed=101, parent=parent_result.artifact.manifest.model_id,
                        architecture=ArchitectureId.TRANSFORMER_V1, reason="invalid")
    with pytest.raises(ValueError, match="architecture"):
        adapt_private_model(
            request=bad_arch, corpus=own_encoded, parent_artifact=store.get(bad_arch.parent_model_id),
            authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=6)),
        )
    bad_tokenizer = _request(own, tokenizer, seed=101, parent=parent_result.artifact.manifest.model_id,
                             tokenizer_hash="f" * 64, reason="invalid")
    with pytest.raises(ValueError, match="hash|tokenizer"):
        adapt_private_model(
            request=bad_tokenizer, corpus=own_encoded, parent_artifact=store.get(bad_tokenizer.parent_model_id),
            authority=ModelTrainingAuthority(TrainingBudget(max_epochs=2, max_steps=6)),
        )


def test_corrupt_parent_is_rejected_before_training(tmp_path):
    parent_result, _, _, store = _train_parent(tmp_path)
    model_id = parent_result.artifact.manifest.model_id
    weights_path = tmp_path / f"{model_id}.pt"
    weights_path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="weights|hash"):
        store.get(model_id)


def test_cold_start_remains_available_and_predictions_are_not_ground_truth():
    from symbiont.modeling.runtime import ModeledOrganismRuntime

    runtime = ModeledOrganismRuntime(organism_id="organism-cold")
    assert runtime.model_registry.records == ()
    prediction = ExperienceRecord(
        record_id="prediction-1", organism_id="organism-cold", tick_class=1,
        context_tokens=("sense.1",), action_token=None, outcome_tokens=("outcome.1",),
        epistemic_status=EpistemicStatus.PREDICTED, evidence_refs=(), confidence_class=1,
        source_kind=SourceKind.MODEL,
    )
    runtime.record_experience(prediction)
    with pytest.raises(ValueError, match="no admissible"):
        runtime.build_private_corpus()
