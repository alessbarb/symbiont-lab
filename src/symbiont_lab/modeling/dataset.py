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
            if any(
                isinstance(position, bool) or not isinstance(position, int)
                for position in positions
            ):
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
        # Preserve causal targets under bounded context. Truncating the raw
        # record from the tail can silently delete every outcome token when an
        # embodied episode contains many sensory context tokens. Instead keep
        # the complete suffix (SEP/action/EPI/SRC/outcomes/EOS) and trim only
        # the oldest/lowest-priority context tokens from the left side.
        suffix: list[str] = ["<SEP>"]
        if record.action_token is not None:
            suffix.append(record.action_token)
        suffix.extend(
            (
                f"<EPI:{record.epistemic_status.value}>",
                f"<SRC:{record.source_kind.value}>",
                *record.outcome_tokens,
                "<EOS>",
            )
        )
        reserved = 1 + len(suffix)  # BOS + full causal suffix
        if reserved > max_sequence:
            # A record whose causal suffix alone cannot fit is not safe to use:
            # dropping an outcome would change the objective.
            continue
        context_budget = max_sequence - reserved
        context = record.context_tokens[-context_budget:] if context_budget else ()
        tokens = ("<BOS>", *context, *suffix)
        encoded = tokenizer.encode_tokens(tokens, max_sequence=max_sequence)
        if len(encoded) < 2:
            continue

        first_outcome_sequence_index = (
            1 + len(context) + 1 + (1 if record.action_token is not None else 0) + 2
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
    if (
        isinstance(context_window, bool)
        or not isinstance(context_window, int)
        or not 8 <= context_window <= 512
    ):
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
        raise ValueError(
            "validation and test splits require at least one observable outcome target"
        )
    return encoded
