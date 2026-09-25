from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import (
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
from symbiont_lab.modeling import (
    TrainingConfig,
    encode_corpus,
    evaluate_candidate,
    train_private_model,
)


@dataclass(frozen=True, slots=True)
class StructuredCausalSeedResult:
    seed: int
    legacy_vocab: int
    structured_vocab: int
    legacy_loss: float
    structured_loss: float
    legacy_gain: float
    structured_gain: float


@dataclass(frozen=True, slots=True)
class StructuredCausalExperienceStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[StructuredCausalSeedResult, ...]
    lower_loss_seeds: int
    positive_gain_seeds: int
    mean_loss_improvement: float
    mean_vocab_reduction_fraction: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _channel_token(index: int) -> str:
    return "motor.channel." + hashlib.sha256(f"channel:{index}".encode()).hexdigest()[:16]


def _records(*, seed: int, ticks: int, structured: bool) -> tuple[ExperienceRecord, ...]:
    organism_id = f"l79-{seed}-{'structured' if structured else 'legacy'}"
    records: list[ExperienceRecord] = []
    for tick in range(ticks):
        state = (seed + tick * 3) % 7
        motor = tuple(((state + tick + channel * 2) % 8) for channel in range(4))
        delivered = tuple(
            max(0, value - ((tick + channel) % 2)) for channel, value in enumerate(motor)
        )
        context = [f"state.opaque.{state}"]
        if structured:
            for channel, (requested, actual) in enumerate(zip(motor, delivered)):
                opaque = _channel_token(channel)
                context.append(f"internal.{opaque}.requested.{requested}")
                context.append(f"internal.{opaque}.delivered.{actual}")
            action = "action.motor.composite"
        else:
            action = (
                "action.motor.pattern."
                + hashlib.sha256(repr((motor, delivered)).encode()).hexdigest()[:24]
            )
        outcome_class = (delivered[0] + 2 * delivered[1] + state) % 5
        records.append(
            ExperienceRecord(
                record_id=f"transition.l79.{seed}.{tick}",
                organism_id=organism_id,
                tick_class=tick,
                context_tokens=tuple(context),
                action_token=action,
                outcome_tokens=(f"outcome.opaque.{outcome_class}",),
                epistemic_status=EpistemicStatus.OBSERVED,
                evidence_refs=(f"evidence.l79.{seed}.{tick}",),
                confidence_class=7,
                source_kind=SourceKind.ACTION_OUTCOME,
            )
        )
    return tuple(records)


def _train(records: tuple[ExperienceRecord, ...], *, seed: int):
    corpus = build_training_corpus(records)
    tokenizer = NativeTokenizer.from_records(corpus.train)
    encoded = encode_corpus(corpus, tokenizer, context_window=48)
    request = TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=48,
        requested_parameters=1_000_000,
        requested_epochs=8,
        requested_steps=48,
        created_tick_class=corpus.manifest.last_tick_class,
        autonomous_stopping=False,
    )
    result = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(
            TrainingBudget(max_parameters=1_000_000, max_epochs=8, max_steps=48)
        ),
        config=TrainingConfig(batch_size=16, patience=8),
    )
    evaluation, _ = evaluate_candidate(result.artifact, encoded)
    return len(tokenizer.vocabulary), evaluation


def run_structured_causal_experience_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 192,
) -> StructuredCausalExperienceStudy:
    normalized = tuple(seeds)
    if not normalized or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must be non-empty unique values")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 96:
        raise ValueError("ticks must be at least 96")

    rows: list[StructuredCausalSeedResult] = []
    for seed in normalized:
        legacy_vocab, legacy = _train(_records(seed=seed, ticks=ticks, structured=False), seed=seed)
        structured_vocab, structured = _train(
            _records(seed=seed, ticks=ticks, structured=True), seed=seed
        )
        rows.append(
            StructuredCausalSeedResult(
                seed=seed,
                legacy_vocab=legacy_vocab,
                structured_vocab=structured_vocab,
                legacy_loss=legacy.candidate.mean_log_loss,
                structured_loss=structured.candidate.mean_log_loss,
                legacy_gain=legacy.gain_over_trivial,
                structured_gain=structured.gain_over_trivial,
            )
        )

    return StructuredCausalExperienceStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(rows),
        lower_loss_seeds=sum(row.structured_loss < row.legacy_loss for row in rows),
        positive_gain_seeds=sum(row.structured_gain > 0.0 for row in rows),
        mean_loss_improvement=sum(row.legacy_loss - row.structured_loss for row in rows)
        / len(rows),
        mean_vocab_reduction_fraction=sum(
            1.0 - row.structured_vocab / row.legacy_vocab for row in rows
        )
        / len(rows),
    )


__all__ = [
    "StructuredCausalExperienceStudy",
    "StructuredCausalSeedResult",
    "run_structured_causal_experience_study",
]
