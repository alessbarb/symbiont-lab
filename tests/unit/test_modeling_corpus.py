import pytest

from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
    SourceKind,
    build_training_corpus,
)


def _record(
    index: int,
    *,
    organism_id: str = "organism.a",
    status: EpistemicStatus = EpistemicStatus.OBSERVED,
) -> ExperienceRecord:
    evidence = (f"evidence.{index}",) if status in {
        EpistemicStatus.OBSERVED,
        EpistemicStatus.SUPPORTED,
        EpistemicStatus.CONTRADICTED,
    } else ()
    return ExperienceRecord(
        record_id=f"record.{index}",
        organism_id=organism_id,
        tick_class=index,
        context_tokens=(f"SENSE:{index}", "STATE:pressure.1"),
        action_token="ACTION:observe",
        outcome_tokens=(f"OUTCOME:{index % 3}",),
        epistemic_status=status,
        evidence_refs=evidence,
        confidence_class=3,
        source_kind=SourceKind.DIRECT,
    )


def test_evidence_backed_status_requires_provenance():
    with pytest.raises(ValueError, match="require evidence_refs"):
        ExperienceRecord(
            record_id="record.1",
            organism_id="organism.a",
            tick_class=1,
            context_tokens=("SENSE:1",),
            action_token=None,
            outcome_tokens=(),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(),
            confidence_class=2,
            source_kind=SourceKind.DIRECT,
        )


def test_experience_record_rejects_unbounded_or_freeform_identifiers():
    with pytest.raises(ValueError, match="printable non-whitespace ASCII"):
        _record(1).__class__(
            record_id="record with spaces",
            organism_id="organism.a",
            tick_class=1,
            context_tokens=("SENSE:1",),
            action_token=None,
            outcome_tokens=(),
            epistemic_status=EpistemicStatus.HYPOTHESIZED,
            evidence_refs=(),
            confidence_class=2,
            source_kind=SourceKind.COGNITIVE,
        )


def test_private_corpus_rejects_cross_organism_mixing():
    with pytest.raises(ValueError, match="exactly one organism"):
        build_training_corpus((_record(1), _record(2, organism_id="organism.b"), _record(3)))


def test_corpus_is_temporal_deterministic_and_has_held_out_tail():
    records = tuple(_record(index) for index in range(1, 11))
    forward = build_training_corpus(records)
    reverse = build_training_corpus(tuple(reversed(records)))

    assert forward.manifest == reverse.manifest
    assert forward.manifest.record_count == 10
    assert forward.manifest.train_count == 7
    assert forward.manifest.validation_count == 1
    assert forward.manifest.test_count == 2
    assert max(record.tick_class for record in forward.train) < min(record.tick_class for record in forward.validation)
    assert max(record.tick_class for record in forward.validation) < min(record.tick_class for record in forward.test)


def test_exact_duplicate_content_does_not_gain_training_weight():
    original = _record(1)
    duplicate = ExperienceRecord(
        record_id="record.duplicate",
        organism_id=original.organism_id,
        tick_class=original.tick_class,
        context_tokens=original.context_tokens,
        action_token=original.action_token,
        outcome_tokens=original.outcome_tokens,
        epistemic_status=original.epistemic_status,
        evidence_refs=original.evidence_refs,
        confidence_class=original.confidence_class,
        source_kind=original.source_kind,
    )
    corpus = build_training_corpus((original, duplicate, _record(2), _record(3), _record(4)))

    assert corpus.manifest.record_count == 4
    assert sum(record.content_hash == original.content_hash for record in (
        *corpus.train, *corpus.validation, *corpus.test
    )) == 1


def test_speculative_and_contradicted_claims_remain_in_ledger_not_v1_training_corpus():
    hypothesis = _record(2, status=EpistemicStatus.HYPOTHESIZED)
    contradicted = _record(3, status=EpistemicStatus.CONTRADICTED)
    supported = _record(4, status=EpistemicStatus.SUPPORTED)
    corpus = build_training_corpus((_record(1), hypothesis, contradicted, supported, _record(5)))
    records = corpus.train + corpus.validation + corpus.test
    ids = {record.record_id for record in records}

    assert hypothesis.record_id not in ids
    assert contradicted.record_id not in ids
    assert supported.record_id in ids
