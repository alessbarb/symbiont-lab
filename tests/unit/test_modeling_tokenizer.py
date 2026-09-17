import pytest

from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
    NativeTokenizer,
    SourceKind,
)


def _record(index: int, token: str) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=f"record.{index}",
        organism_id="organism.a",
        tick_class=index,
        context_tokens=(token, "STATE:pressure.1"),
        action_token="ACTION:repair",
        outcome_tokens=("OUTCOME:integrity.up",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"evidence.{index}",),
        confidence_class=4,
        source_kind=SourceKind.ACTION_OUTCOME,
    )


def test_native_tokenizer_is_deterministic_across_record_order():
    records = (_record(1, "SENSE:a"), _record(2, "SENSE:b"))
    forward = NativeTokenizer.from_records(records)
    reverse = NativeTokenizer.from_records(tuple(reversed(records)))

    assert forward.vocabulary == reverse.vocabulary
    assert forward.tokenizer_hash == reverse.tokenizer_hash


def test_native_tokenizer_round_trips_known_record_tokens():
    record = _record(1, "SENSE:a")
    tokenizer = NativeTokenizer.from_records((record,))
    encoded = tokenizer.encode_record(record)
    decoded = tokenizer.decode(encoded)

    assert decoded[0] == "<BOS>"
    assert decoded[-1] == "<EOS>"
    assert "SENSE:a" in decoded
    assert "<EPI:observed>" in decoded
    assert "<SRC:action_outcome>" in decoded


def test_native_tokenizer_maps_unseen_native_token_to_unknown():
    tokenizer = NativeTokenizer.from_records((_record(1, "SENSE:a"),))
    encoded = tokenizer.encode_tokens(("SENSE:not-yet-known",))

    assert encoded == (tokenizer.token_to_id["<UNK>"],)


def test_native_tokenizer_enforces_bounded_vocabulary():
    records = tuple(_record(index, f"SENSE:{index}") for index in range(20))
    tokenizer = NativeTokenizer.from_records(records, max_vocab=12)

    assert len(tokenizer.vocabulary) == 12


def test_native_tokenizer_rejects_out_of_range_decode_id():
    tokenizer = NativeTokenizer.from_records((_record(1, "SENSE:a"),))

    with pytest.raises(ValueError, match="outside vocabulary"):
        tokenizer.decode((len(tokenizer.vocabulary),))
