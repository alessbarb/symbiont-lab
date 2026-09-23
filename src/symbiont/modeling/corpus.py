from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from .experience import EpistemicStatus, ExperienceRecord, SourceKind


# NOTE(design): Private SLM v1 is deliberately conservative: speculative, predicted,
# contradicted and retired claims remain inspectable in the ledger but are not
# next-token training targets. Later multi-task objectives may learn from those
# states explicitly without conflating them with factual outcome evidence.
_DEFAULT_ALLOWED_STATES = frozenset({
    EpistemicStatus.OBSERVED,
    EpistemicStatus.SUPPORTED,
})


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    schema_version: int
    organism_id: str
    record_count: int
    train_count: int
    validation_count: int
    test_count: int
    first_tick_class: int
    last_tick_class: int
    corpus_hash: str


@dataclass(frozen=True, slots=True)
class TrainingCorpus:
    train: tuple[ExperienceRecord, ...]
    validation: tuple[ExperienceRecord, ...]
    test: tuple[ExperienceRecord, ...]
    manifest: CorpusManifest


def _canonical_corpus_hash(records: tuple[ExperienceRecord, ...]) -> str:
    payload = [record.canonical_payload() for record in records]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _split_counts(total: int) -> tuple[int, int, int]:
    if total < 3:
        raise ValueError("at least three unique experience records are required")
    train = max(1, int(total * 0.70))
    validation = max(1, int(total * 0.15))
    test = total - train - validation
    if test < 1:
        train -= 1
        test = 1
    return train, validation, test


def _admissible_record(record: ExperienceRecord, allowed_states: frozenset[EpistemicStatus]) -> bool:
    if record.epistemic_status not in allowed_states:
        return False
    if record.source_kind is not SourceKind.MODEL:
        return True
    # Generated content becomes trainable only after independent evidence has
    # explicitly supported it. A contradiction remains scientifically useful
    # in the ledger but never becomes a positive next-token target.
    return record.epistemic_status is EpistemicStatus.SUPPORTED and bool(record.evidence_refs)


def build_training_corpus(
    records: Iterable[ExperienceRecord],
    *,
    allowed_states: frozenset[EpistemicStatus] = _DEFAULT_ALLOWED_STATES,
    max_records: int = 8192,
) -> TrainingCorpus:
    """Build one deterministic temporal corpus for a single organism.

    Exact duplicate episode content is collapsed while the earliest canonical
    record is retained. Splits are contiguous in organism time, preventing
    future episodes from leaking into the training side of an earlier test.
    Private SLM v1 admits only evidence-backed states by default.
    """

    if isinstance(max_records, bool) or not isinstance(max_records, int) or not 3 <= max_records <= 65536:
        raise ValueError("max_records must be an integer within [3, 65536]")
    if not isinstance(allowed_states, frozenset) or not allowed_states:
        raise ValueError("allowed_states must be a non-empty frozenset")
    if any(not isinstance(state, EpistemicStatus) for state in allowed_states):
        raise ValueError("allowed_states contains an invalid epistemic status")

    source = tuple(records)
    if any(not isinstance(record, ExperienceRecord) for record in source):
        raise ValueError("records must contain ExperienceRecord values")
    selected = tuple(record for record in source if _admissible_record(record, allowed_states))
    if not selected:
        raise ValueError("no admissible experience records")

    organism_ids = {record.organism_id for record in selected}
    if len(organism_ids) != 1:
        raise ValueError("a private training corpus must belong to exactly one organism")

    ordered = sorted(selected, key=lambda record: (record.tick_class, record.record_id))
    unique: list[ExperienceRecord] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()
    for record in ordered:
        if record.record_id in seen_ids:
            raise ValueError("duplicate record_id in experience corpus")
        seen_ids.add(record.record_id)
        if record.content_hash in seen_hashes:
            continue
        seen_hashes.add(record.content_hash)
        unique.append(record)
        if len(unique) >= max_records:
            break

    canonical = tuple(unique)
    train_count, validation_count, test_count = _split_counts(len(canonical))
    validation_start = train_count
    test_start = train_count + validation_count

    train = canonical[:validation_start]
    validation = canonical[validation_start:test_start]
    test = canonical[test_start:]
    manifest = CorpusManifest(
        schema_version=1,
        organism_id=canonical[0].organism_id,
        record_count=len(canonical),
        train_count=len(train),
        validation_count=len(validation),
        test_count=len(test),
        first_tick_class=canonical[0].tick_class,
        last_tick_class=canonical[-1].tick_class,
        corpus_hash=_canonical_corpus_hash(canonical),
    )
    return TrainingCorpus(train=train, validation=validation, test=test, manifest=manifest)
