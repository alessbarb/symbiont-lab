from __future__ import annotations

from dataclasses import dataclass

from symbiont.modeling.corpus import TrainingCorpus
from symbiont.modeling.tokenizer import NativeTokenizer


@dataclass(frozen=True, slots=True)
class EncodedSplit:
    sequences: tuple[tuple[int, ...], ...]
    record_ids: tuple[str, ...]
    outcome_target_positions: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if not (len(self.sequences) == len(self.record_ids) == len(self.outcome_target_positions)):
            raise ValueError("encoded split sequence/id/target length mismatch")
        if any(len(sequence) < 2 for sequence in self.sequences):
            raise ValueError("every encoded sequence must contain at least two tokens")
        for sequence, positions in zip(self.sequences, self.outcome_target_positions):
            if any(isinstance(position, bool) or not isinstance(position, int) for position in positions):
                raise ValueError("outcome target positions must be integers")
            if any(position < 0 or position >= len(sequence) - 1 for position in positions):
                raise ValueError("outcome target position outside causal sequence")
            if tuple(sorted(set(positions))) != positions:
                raise ValueError("outcome target positions must be unique and ordered")

    @property
    def outcome_predictions(self) -> int:
        return sum(len(positions) for positions in self.outcome_target_positions)


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
    outcome_positions: list[tuple[int, ...]] = []
    max_sequence = context_window + 1
    for record in records:
        encoded = tokenizer.encode_record(record, max_sequence=max_sequence)
        if len(encoded) < 2:
            continue
        # Full token layout is:
        # BOS, context..., SEP, [action], EPI, SRC, outcomes..., EOS.
        # A logit at index n predicts sequence token n+1, so each outcome token
        # maps to the preceding input/logit position.
        first_outcome_sequence_index = (
            1 + len(record.context_tokens) + 1
            + (1 if record.action_token is not None else 0)
            + 2
        )
        positions = tuple(
            sequence_index - 1
            for sequence_index in range(
                first_outcome_sequence_index,
                first_outcome_sequence_index + len(record.outcome_tokens),
            )
            if 1 <= sequence_index < len(encoded)
        )
        sequences.append(encoded)
        record_ids.append(record.record_id)
        outcome_positions.append(positions)
    if not sequences:
        raise ValueError("encoded corpus split contains no usable sequences")
    return EncodedSplit(tuple(sequences), tuple(record_ids), tuple(outcome_positions))


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
    encoded = EncodedCorpus(
        train=_encode_split(corpus.train, tokenizer, context_window),
        validation=_encode_split(corpus.validation, tokenizer, context_window),
        test=_encode_split(corpus.test, tokenizer, context_window),
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        vocab_size=len(tokenizer.vocabulary),
        pad_id=mapping["<PAD>"],
    )
    if encoded.validation.outcome_predictions < 1 or encoded.test.outcome_predictions < 1:
        raise ValueError("validation and test splits require at least one observable outcome target")
    return encoded
