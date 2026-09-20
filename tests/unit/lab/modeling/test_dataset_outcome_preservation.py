from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
    NativeTokenizer,
    SourceKind,
    build_training_corpus,
)
from symbiont_lab.modeling.dataset import encode_corpus


def _embodied_record(index: int) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=f"embodied.{index}",
        organism_id="embodied-organism",
        tick_class=index,
        context_tokens=tuple(f"sense.{slot}" for slot in range(48)),
        action_token=f"action.motor.{index % 2}",
        outcome_tokens=(f"outcome.motor.delivered.{index % 8}",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"evidence.{index}",),
        confidence_class=7,
        source_kind=SourceKind.ACTION_OUTCOME,
    )


def test_bounded_encoding_preserves_observable_outcomes_after_long_context():
    corpus = build_training_corpus(tuple(_embodied_record(i) for i in range(12)))
    tokenizer = NativeTokenizer.from_records(corpus.train)

    encoded = encode_corpus(corpus, tokenizer, context_window=32)

    assert encoded.train.outcome_predictions > 0
    assert encoded.validation.outcome_predictions > 0
    assert encoded.test.outcome_predictions > 0
    assert all(len(sequence) <= 33 for sequence in (
        *encoded.train.sequences,
        *encoded.validation.sequences,
        *encoded.test.sequences,
    ))
