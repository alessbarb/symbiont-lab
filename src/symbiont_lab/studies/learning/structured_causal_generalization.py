from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import random

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
class CausalGeneralizationArm:
    vocab_size: int
    unique_train_actions: int
    unseen_test_action_fraction: float
    unseen_test_motor_token_fraction: float
    candidate_loss: float
    gain_over_trivial: float
    parameter_count: int


@dataclass(frozen=True, slots=True)
class CausalGeneralizationSeedResult:
    seed: int
    legacy: CausalGeneralizationArm
    structured: CausalGeneralizationArm
    structured_loss_improvement: float
    structured_vocab_reduction_fraction: float


@dataclass(frozen=True, slots=True)
class StructuredCausalGeneralizationStudy:
    seeds: tuple[int, ...]
    ticks: int
    channels: int
    per_seed: tuple[CausalGeneralizationSeedResult, ...]
    lower_loss_seeds: int
    positive_gain_seeds: int
    mean_loss_improvement: float
    mean_vocab_reduction_fraction: float
    mean_legacy_unseen_action_fraction: float
    mean_structured_unseen_motor_token_fraction: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _channel_token(index: int) -> str:
    return "motor.channel." + hashlib.sha256(f"l79v2-channel:{index}".encode()).hexdigest()[:16]


def _motor_trace(*, seed: int, ticks: int, channels: int) -> tuple[tuple[int, tuple[int, ...], tuple[int, ...], int], ...]:
    """Deterministic high-cardinality motor history with compositional outcomes.

    Whole motor vectors are effectively unique over the temporal split while
    per-channel identities and magnitude classes recur. The hidden outcome law
    is compositional and never appears as a semantic label in organism data.
    """
    rng = random.Random(seed)
    rows: list[tuple[int, tuple[int, ...], tuple[int, ...], int]] = []
    latent = seed % 11
    for tick in range(ticks):
        requested = tuple(rng.randrange(8) for _ in range(channels))
        delivered = tuple(
            max(0, min(7, value - (1 if rng.random() < 0.22 else 0)))
            for value in requested
        )
        state = (latent + tick // 9 + requested[-1]) % 11
        # Depend on reusable components, not whole-vector identity.
        outcome = (
            state
            + delivered[0]
            + 2 * delivered[1]
            + 3 * delivered[2]
            + (delivered[3] >= 4)
        ) % 7
        rows.append((state, requested, delivered, outcome))
        latent = (latent + delivered[0] - delivered[1]) % 11
    return tuple(rows)


def _records(
    trace: tuple[tuple[int, tuple[int, ...], tuple[int, ...], int], ...],
    *,
    seed: int,
    structured: bool,
) -> tuple[ExperienceRecord, ...]:
    organism_id = f"l79v2-{seed}-{'structured' if structured else 'legacy'}"
    records: list[ExperienceRecord] = []
    for tick, (state, requested, delivered, outcome) in enumerate(trace):
        context = [f"state.opaque.{state}"]
        if structured:
            for channel, (ask, actual) in enumerate(zip(requested, delivered)):
                opaque = _channel_token(channel)
                context.append(f"internal.{opaque}.requested.{ask}")
                context.append(f"internal.{opaque}.delivered.{actual}")
            action = "action.motor.composite"
        else:
            payload = repr((requested, delivered)).encode()
            action = "action.motor.pattern." + hashlib.sha256(payload).hexdigest()[:24]

        records.append(ExperienceRecord(
            record_id=f"transition.l79v2.{seed}.{tick}",
            organism_id=organism_id,
            tick_class=tick,
            context_tokens=tuple(context),
            action_token=action,
            outcome_tokens=(f"outcome.opaque.{outcome}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.l79v2.{seed}.{tick}",),
            confidence_class=7,
            source_kind=SourceKind.ACTION_OUTCOME,
        ))
    return tuple(records)


def _unseen_fraction(values: tuple[str, ...], vocabulary: set[str]) -> float:
    if not values:
        return 0.0
    return sum(value not in vocabulary for value in values) / len(values)


def _train(records: tuple[ExperienceRecord, ...], *, seed: int) -> CausalGeneralizationArm:
    corpus = build_training_corpus(records)
    tokenizer = NativeTokenizer.from_records(corpus.train)
    vocabulary = set(tokenizer.vocabulary)
    encoded = encode_corpus(corpus, tokenizer, context_window=96)

    request = TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=96,
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

    test_actions = tuple(
        record.action_token
        for record in corpus.test
        if record.action_token is not None
    )
    test_motor_tokens = tuple(
        token
        for record in corpus.test
        for token in record.context_tokens
        if "motor.channel." in token
    )
    return CausalGeneralizationArm(
        vocab_size=len(tokenizer.vocabulary),
        unique_train_actions=len({
            record.action_token for record in corpus.train if record.action_token is not None
        }),
        unseen_test_action_fraction=_unseen_fraction(test_actions, vocabulary),
        unseen_test_motor_token_fraction=_unseen_fraction(test_motor_tokens, vocabulary),
        candidate_loss=evaluation.candidate.mean_log_loss,
        gain_over_trivial=evaluation.gain_over_trivial,
        parameter_count=result.artifact.manifest.parameter_count,
    )


def run_structured_causal_generalization_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 768,
    channels: int = 8,
) -> StructuredCausalGeneralizationStudy:
    normalized = tuple(seeds)
    if not normalized or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must be non-empty unique values")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 384 <= ticks <= 4096:
        raise ValueError("ticks must be within [384, 4096]")
    if isinstance(channels, bool) or not isinstance(channels, int) or not 4 <= channels <= 32:
        raise ValueError("channels must be within [4, 32]")

    rows: list[CausalGeneralizationSeedResult] = []
    for seed in normalized:
        trace = _motor_trace(seed=seed, ticks=ticks, channels=channels)
        legacy = _train(_records(trace, seed=seed, structured=False), seed=seed)
        structured = _train(_records(trace, seed=seed, structured=True), seed=seed)
        rows.append(CausalGeneralizationSeedResult(
            seed=seed,
            legacy=legacy,
            structured=structured,
            structured_loss_improvement=legacy.candidate_loss - structured.candidate_loss,
            structured_vocab_reduction_fraction=1.0 - structured.vocab_size / legacy.vocab_size,
        ))

    return StructuredCausalGeneralizationStudy(
        seeds=normalized,
        ticks=ticks,
        channels=channels,
        per_seed=tuple(rows),
        lower_loss_seeds=sum(row.structured.candidate_loss < row.legacy.candidate_loss for row in rows),
        positive_gain_seeds=sum(row.structured.gain_over_trivial > 0.0 for row in rows),
        mean_loss_improvement=sum(row.structured_loss_improvement for row in rows) / len(rows),
        mean_vocab_reduction_fraction=sum(row.structured_vocab_reduction_fraction for row in rows) / len(rows),
        mean_legacy_unseen_action_fraction=sum(row.legacy.unseen_test_action_fraction for row in rows) / len(rows),
        mean_structured_unseen_motor_token_fraction=sum(row.structured.unseen_test_motor_token_fraction for row in rows) / len(rows),
    )


__all__ = [
    "CausalGeneralizationArm",
    "CausalGeneralizationSeedResult",
    "StructuredCausalGeneralizationStudy",
    "run_structured_causal_generalization_study",
]
