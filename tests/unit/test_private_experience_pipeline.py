from __future__ import annotations

from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
    PrivateModelOrganismRuntime,
    SourceKind,
    build_training_corpus,
)


def _direct(record_id: str, tick: int) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=record_id,
        organism_id="organism-a",
        tick_class=tick,
        context_tokens=(f"sense.{tick}",),
        action_token=None,
        outcome_tokens=(f"outcome.{tick}",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"evidence.{tick}",),
        confidence_class=7,
        source_kind=SourceKind.DIRECT,
    )


def test_raw_model_prediction_cannot_train_its_successor():
    records = [_direct(f"r{tick}", tick) for tick in range(4)]
    prediction = ExperienceRecord(
        record_id="model.p1",
        organism_id="organism-a",
        tick_class=5,
        context_tokens=("sense.1",),
        action_token=None,
        outcome_tokens=("outcome.predicted",),
        epistemic_status=EpistemicStatus.PREDICTED,
        evidence_refs=(),
        confidence_class=6,
        source_kind=SourceKind.MODEL,
    )
    corpus = build_training_corpus((*records, prediction))
    all_records = corpus.train + corpus.validation + corpus.test
    assert prediction.record_id not in {record.record_id for record in all_records}


def test_independently_supported_model_prediction_can_enter_future_corpus():
    records = [_direct(f"r{tick}", tick) for tick in range(4)]
    validated = ExperienceRecord(
        record_id="validation.p1",
        organism_id="organism-a",
        tick_class=5,
        context_tokens=("sense.1",),
        action_token=None,
        outcome_tokens=("outcome.predicted",),
        epistemic_status=EpistemicStatus.SUPPORTED,
        evidence_refs=("evidence.independent",),
        confidence_class=6,
        source_kind=SourceKind.MODEL,
    )
    corpus = build_training_corpus((*records, validated))
    all_records = corpus.train + corpus.validation + corpus.test
    assert validated.record_id in {record.record_id for record in all_records}


def test_private_runtime_captures_abstract_tick_and_restores_ledger():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-runtime",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    result = runtime.tick()
    assert len(runtime.experience_ledger.records) == 1
    record = runtime.experience_ledger.records[0]
    assert record.tick_class == result.tick
    assert all("system_load" not in token and "storage_pressure" not in token for token in record.context_tokens)
    assert all(not token.startswith("event.") for token in record.context_tokens)

    restored = PrivateModelOrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored.capture_private_experience is True
    assert restored.experience_ledger.records == runtime.experience_ledger.records
