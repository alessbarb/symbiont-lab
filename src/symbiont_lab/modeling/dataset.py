from __future__ import annotations

from dataclasses import dataclass

from symbiont.modeling.corpus import TrainingCorpus
from symbiont.modeling.tokenizer import NativeTokenizer


@dataclass(frozen=True, slots=True)
class EncodedSplit:
    sequences: tuple[tuple[int, ...], ...]
    record_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sequences) != len(self.record_ids):
            raise ValueError("encoded split sequence/id length mismatch")
        if any(len(sequence) < 2 for sequence in self.sequences):
            raise ValueError("every encoded sequence must contain at least two tokens")


@dataclass(frozen=True, slots=True)
class EncodedCorpus:
    train: EncodedSplit
    validation: EncodedSplit
    test: EncodedSplit
    corpus_hash: str
    tokenizer_hash: str
    vocab_size: int
    pad_id: int


def _encode_split(records, tokenizer: NativeTokenizer, context_window: int) -> EncodedSplit:
    sequences: list[tuple[int, ...]] = []
    record_ids: list[str] = []
    max_sequence = context_window + 1
    for record in records:
        encoded = tokenizer.encode_record(record, max_sequence=max_sequence)
        if len(encoded) < 2:
            continue
        sequences.append(encoded)
        record_ids.append(record.record_id)
    if not sequences:
        raise ValueError("encoded corpus split contains no usable sequences")
    return EncodedSplit(tuple(sequences), tuple(record_ids))


def encode_corpus(
    corpus: TrainingCorpus,
    tokenizer: NativeTokenizer,
    *,
    context_window: int,
) -> EncodedCorpus:
    if not isinstance(corpus, TrainingCorpus):
        raise ValueError("corpus must be a TrainingCorpus")
    if not isinstance(tokenizer, NativeTokenizer):
        raise ValueError("tokenizer must be a NativeTokenizer")
    if isinstance(context_window, bool) or not isinstance(context_window, int) or not 8 <= context_window <= 512:
        raise ValueError("context_window must be within [8, 512]")
    mapping = tokenizer.token_to_id
    return EncodedCorpus(
        train=_encode_split(corpus.train, tokenizer, context_window),
        validation=_encode_split(corpus.validation, tokenizer, context_window),
        test=_encode_split(corpus.test, tokenizer, context_window),
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        vocab_size=len(tokenizer.vocabulary),
        pad_id=mapping["<PAD>"],
    )
