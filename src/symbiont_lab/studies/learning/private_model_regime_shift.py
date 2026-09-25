from __future__ import annotations

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
    TrainingRequest,
    build_training_corpus,
)
from symbiont_lab.modeling import TrainingConfig, encode_corpus, train_private_model
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model

_OUTCOME_PERMUTATION = (2, 4, 1, 0, 3)


@dataclass(frozen=True, slots=True)
class SymmetricRegimeSeedResult:
    seed: int
    pre_loss: float
    stale_post_loss: float
    retrained_post_loss: float
    stale_degradation: float
    recovery: float
    recovered_vs_pre_gap: float


@dataclass(frozen=True, slots=True)
class SymmetricRegimeStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[SymmetricRegimeSeedResult, ...]
    mean_stale_degradation: float
    mean_recovery: float
    mean_recovered_vs_pre_gap: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must contain between 1 and 16 entries")
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16:
        raise ValueError("seeds must contain between 1 and 16 entries")
    if len(set(normalized)) != len(normalized) or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized
    ):
        raise ValueError("seeds must be unique integers")
    return normalized


def _history(
    *, organism_id: str, seed: int, ticks: int, shifted: bool
) -> tuple[ExperienceRecord, ...]:
    """Create matched regimes with identical context/action distribution and bijective outcome relabeling."""

    records: list[ExperienceRecord] = []
    phase = seed % 5
    for tick in range(ticks):
        left = (phase + tick) % 5
        right = (phase * 3 + tick * 2) % 7
        action = (left + right + tick) % 3
        base_outcome = (left * 2 + right + action) % 5
        outcome = _OUTCOME_PERMUTATION[base_outcome] if shifted else base_outcome
        records.append(
            ExperienceRecord(
                record_id=f"episode.{organism_id}.{tick}",
                organism_id=organism_id,
                tick_class=tick,
                context_tokens=(f"sense.{left}", f"sense.{right}"),
                action_token=f"action.{action}",
                outcome_tokens=(f"outcome.{outcome}",),
                epistemic_status=EpistemicStatus.OBSERVED,
                evidence_refs=(f"evidence.{organism_id}.{tick}",),
                confidence_class=7,
                source_kind=SourceKind.ACTION_OUTCOME,
            )
        )
    return tuple(records)


def _request(*, corpus, tokenizer_hash: str, seed: int) -> TrainingRequest:
    return TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=32,
        requested_parameters=5_000_000,
        requested_epochs=8,
        requested_steps=512,
        created_tick_class=corpus.manifest.last_tick_class,
    )


def _train(*, corpus, encoded, tokenizer_hash: str, seed: int):
    return train_private_model(
        request=_request(corpus=corpus, tokenizer_hash=tokenizer_hash, seed=seed),
        corpus=encoded,
        authority=ModelTrainingAuthority(),
        config=TrainingConfig(batch_size=16, patience=3),
        device="cpu",
    )


def _loss(training, encoded) -> float:
    model = load_artifact_model(
        training.artifact,
        vocab_size=encoded.vocab_size,
        pad_id=encoded.pad_id,
        device="cpu",
    )
    return evaluate_outcome_model(
        model,
        encoded.test,
        pad_id=encoded.pad_id,
        context_window=training.artifact.manifest.context_window,
    ).mean_log_loss


def run_private_model_symmetric_regime_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> SymmetricRegimeStudy:
    """Matched concept-drift control with preserved context and outcome marginals.

    The post-shift regime is a fixed bijective permutation of outcome identities.
    Contexts, actions, sequence length and outcome-frequency multiset are unchanged,
    so stale-vs-pre loss is not confounded by a different target entropy surface.
    """

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 64 <= ticks <= 4096:
        raise ValueError("ticks must be within [64, 4096]")

    results: list[SymmetricRegimeSeedResult] = []
    for seed in normalized:
        organism_id = f"symmetric-regime-{seed}"
        pre_corpus = build_training_corpus(
            _history(organism_id=organism_id, seed=seed, ticks=ticks, shifted=False)
        )
        post_corpus = build_training_corpus(
            _history(organism_id=organism_id, seed=seed, ticks=ticks, shifted=True)
        )
        tokenizer = NativeTokenizer.from_records((*pre_corpus.train, *post_corpus.train))
        pre_encoded = encode_corpus(pre_corpus, tokenizer, context_window=32)
        post_encoded = encode_corpus(post_corpus, tokenizer, context_window=32)

        pre_training = _train(
            corpus=pre_corpus,
            encoded=pre_encoded,
            tokenizer_hash=tokenizer.tokenizer_hash,
            seed=seed,
        )
        post_training = _train(
            corpus=post_corpus,
            encoded=post_encoded,
            tokenizer_hash=tokenizer.tokenizer_hash,
            seed=seed + 40_000,
        )

        pre_loss = _loss(pre_training, pre_encoded)
        stale_post_loss = _loss(pre_training, post_encoded)
        retrained_post_loss = _loss(post_training, post_encoded)
        results.append(
            SymmetricRegimeSeedResult(
                seed=seed,
                pre_loss=pre_loss,
                stale_post_loss=stale_post_loss,
                retrained_post_loss=retrained_post_loss,
                stale_degradation=stale_post_loss - pre_loss,
                recovery=stale_post_loss - retrained_post_loss,
                recovered_vs_pre_gap=retrained_post_loss - pre_loss,
            )
        )

    count = len(results)
    return SymmetricRegimeStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        mean_stale_degradation=sum(item.stale_degradation for item in results) / count,
        mean_recovery=sum(item.recovery for item in results) / count,
        mean_recovered_vs_pre_gap=sum(item.recovered_vs_pre_gap for item in results) / count,
    )


__all__ = [
    "SymmetricRegimeSeedResult",
    "SymmetricRegimeStudy",
    "run_private_model_symmetric_regime_study",
]
