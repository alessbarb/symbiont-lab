from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from .experience import ExperienceRecord

_RESERVED = ("<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>")
_MAX_VOCAB = 32768
_MAX_SEQUENCE = 2048


def _record_tokens(record: ExperienceRecord) -> tuple[str, ...]:
    tokens: list[str] = ["<BOS>"]
    tokens.extend(record.context_tokens)
    tokens.append("<SEP>")
    if record.action_token is not None:
        tokens.append(record.action_token)
    tokens.append(f"<EPI:{record.epistemic_status.value}>")
    tokens.append(f"<SRC:{record.source_kind.value}>")
    tokens.extend(record.outcome_tokens)
    tokens.append("<EOS>")
    return tuple(tokens)


@dataclass(frozen=True, slots=True)
class NativeTokenizer:
    """Deterministic closed tokenizer for organism-native structured tokens."""

    vocabulary: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.vocabulary, tuple):
            raise ValueError("vocabulary must be a tuple")
        if len(self.vocabulary) < len(_RESERVED) or len(self.vocabulary) > _MAX_VOCAB:
            raise ValueError("vocabulary exceeds bounded size")
        if self.vocabulary[: len(_RESERVED)] != _RESERVED:
            raise ValueError("reserved tokens must occupy the canonical prefix")
        if len(set(self.vocabulary)) != len(self.vocabulary):
            raise ValueError("vocabulary tokens must be unique")

    @classmethod
    def from_records(
        cls,
        records: Iterable[ExperienceRecord],
        *,
        max_vocab: int = _MAX_VOCAB,
    ) -> "NativeTokenizer":
        if isinstance(max_vocab, bool) or not isinstance(max_vocab, int):
            raise ValueError("max_vocab must be an integer")
        if not len(_RESERVED) <= max_vocab <= _MAX_VOCAB:
            raise ValueError(f"max_vocab must be within [{len(_RESERVED)}, {_MAX_VOCAB}]")

        seen: set[str] = set()
        for record in records:
            if not isinstance(record, ExperienceRecord):
                raise ValueError("records must contain ExperienceRecord values")
            for token in _record_tokens(record):
                if token not in _RESERVED:
                    seen.add(token)
        available = max_vocab - len(_RESERVED)
        vocabulary = _RESERVED + tuple(sorted(seen)[:available])
        return cls(vocabulary=vocabulary)

    @property
    def token_to_id(self) -> dict[str, int]:
        return {token: index for index, token in enumerate(self.vocabulary)}

    @property
    def tokenizer_hash(self) -> str:
        encoded = json.dumps(self.vocabulary, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def encode_tokens(
        self, tokens: Iterable[str], *, max_sequence: int = _MAX_SEQUENCE
    ) -> tuple[int, ...]:
        if isinstance(max_sequence, bool) or not isinstance(max_sequence, int):
            raise ValueError("max_sequence must be an integer")
        if not 1 <= max_sequence <= _MAX_SEQUENCE:
            raise ValueError(f"max_sequence must be within [1, {_MAX_SEQUENCE}]")
        mapping = self.token_to_id
        unknown = mapping["<UNK>"]
        encoded: list[int] = []
        for token in tokens:
            if not isinstance(token, str) or not token:
                raise ValueError("tokens must be non-empty strings")
            encoded.append(mapping.get(token, unknown))
            if len(encoded) >= max_sequence:
                break
        return tuple(encoded)

    def encode_record(
        self, record: ExperienceRecord, *, max_sequence: int = _MAX_SEQUENCE
    ) -> tuple[int, ...]:
        if not isinstance(record, ExperienceRecord):
            raise ValueError("record must be an ExperienceRecord")
        return self.encode_tokens(_record_tokens(record), max_sequence=max_sequence)

    def decode(self, token_ids: Iterable[int]) -> tuple[str, ...]:
        decoded: list[str] = []
        for token_id in token_ids:
            if isinstance(token_id, bool) or not isinstance(token_id, int):
                raise ValueError("token ids must be integers")
            if not 0 <= token_id < len(self.vocabulary):
                raise ValueError("token id outside vocabulary")
            decoded.append(self.vocabulary[token_id])
        return tuple(decoded)
