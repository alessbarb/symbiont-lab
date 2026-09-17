from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import (
    ArchitectureId,
    ModelObjective,
    ModelTrainingAuthority,
    NativeTokenizer,
    TrainingRequest,
    build_training_corpus,
)
from symbiont_lab.modeling import TrainingConfig, adapt_private_model, encode_corpus, train_private_model
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model

from .private_model_regime_shift import _history


@dataclass(frozen=True, slots=True)
class AdaptationSeedResult:
    seed: int
    pre_shift_loss: float
    stale_post_loss: float
    fresh_post_loss: float
    adapted_post_loss: float
    stale_degradation: float
    fresh_recovery: float
    adapted_recovery: float
    adapted_vs_fresh: float
    adapted_vs_stale: float
    lineage_valid: bool
    adaptation_cost: int


@dataclass(frozen=True, slots=True)
class PrivateModelAdaptationStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[AdaptationSeedResult, ...]
    mean_stale_degradation: float
    mean_fresh_recovery: float
    mean_adapted_recovery: float
    mean_adapted_vs_fresh: float
    mean_adapted_vs_stale: float
    all_lineage_valid: bool
    mean_adaptation_cost: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must contain between 1 and 16 entries")
    values = tuple(seeds)
    if not values or len(values) > 16 or len(set(values)) != len(values):
        raise ValueError("seeds must contain unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in values):
        raise ValueError("seeds must be integers")
    return values


def _request(corpus, tokenizer: NativeTokenizer, *, seed: int, parent: str | None = None) -> TrainingRequest:
    return TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=32,
        requested_parameters=5_000_000,
        requested_epochs=8,
        requested_steps=512,
        created_tick_class=corpus.manifest.last_tick_class,
        parent_model_id=parent,
        adaptation_reason="symmetric post-shift direct experience" if parent is not None else None,
    )


def _loss(training, encoded) -> float:
    model = load_artifact_model(training.artifact, vocab_size=encoded.vocab_size, pad_id=encoded.pad_id)
    return evaluate_outcome_model(
        model, encoded.test, pad_id=encoded.pad_id,
        context_window=training.artifact.manifest.context_window,
    ).mean_log_loss


def run_private_model_adaptation_study(
    *, seeds: Sequence[int] = (101, 127, 149), ticks: int = 128,
) -> PrivateModelAdaptationStudy:
    """Compare stale, cold-start fresh, and bounded parent-initialized adaptation."""
    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 64 <= ticks <= 4096:
        raise ValueError("ticks must be within [64, 4096]")

    results: list[AdaptationSeedResult] = []
    for seed in normalized:
        organism_id = f"adaptation-{seed}"
        pre_corpus = build_training_corpus(_history(organism_id=organism_id, seed=seed, ticks=ticks, shifted=False))
        post_corpus = build_training_corpus(_history(organism_id=organism_id, seed=seed, ticks=ticks, shifted=True))
        tokenizer = NativeTokenizer.from_records((*pre_corpus.train, *post_corpus.train))
        pre_encoded = encode_corpus(pre_corpus, tokenizer, context_window=32)
        post_encoded = encode_corpus(post_corpus, tokenizer, context_window=32)
        authority = ModelTrainingAuthority()
        config = TrainingConfig(batch_size=16, patience=3)
        pre_training = train_private_model(
            request=_request(pre_corpus, tokenizer, seed=seed), corpus=pre_encoded,
            authority=authority, config=config,
        )
        fresh_training = train_private_model(
            request=_request(post_corpus, tokenizer, seed=seed + 40_000), corpus=post_encoded,
            authority=authority, config=config,
        )
        adapted_training = adapt_private_model(
            request=_request(post_corpus, tokenizer, seed=seed, parent=pre_training.artifact.manifest.model_id),
            corpus=post_encoded, parent_artifact=pre_training.artifact,
            authority=authority, config=config,
        )
        pre_loss = _loss(pre_training, pre_encoded)
        stale_post = _loss(pre_training, post_encoded)
        fresh_post = _loss(fresh_training, post_encoded)
        adapted_post = _loss(adapted_training, post_encoded)
        results.append(AdaptationSeedResult(
            seed=seed, pre_shift_loss=pre_loss, stale_post_loss=stale_post,
            fresh_post_loss=fresh_post, adapted_post_loss=adapted_post,
            stale_degradation=stale_post - pre_loss,
            fresh_recovery=stale_post - fresh_post,
            adapted_recovery=stale_post - adapted_post,
            adapted_vs_fresh=fresh_post - adapted_post,
            adapted_vs_stale=stale_post - adapted_post,
            lineage_valid=(
                adapted_training.artifact.manifest.parent_model_id == pre_training.artifact.manifest.model_id
                and adapted_training.artifact.manifest.ancestor_model_id == pre_training.artifact.manifest.model_id
                and adapted_training.artifact.manifest.generation == 1
            ),
            adaptation_cost=adapted_training.steps_completed,
        ))
    count = len(results)
    return PrivateModelAdaptationStudy(
        seeds=normalized, ticks=ticks, per_seed=tuple(results),
        mean_stale_degradation=sum(item.stale_degradation for item in results) / count,
        mean_fresh_recovery=sum(item.fresh_recovery for item in results) / count,
        mean_adapted_recovery=sum(item.adapted_recovery for item in results) / count,
        mean_adapted_vs_fresh=sum(item.adapted_vs_fresh for item in results) / count,
        mean_adapted_vs_stale=sum(item.adapted_vs_stale for item in results) / count,
        all_lineage_valid=all(item.lineage_valid for item in results),
        mean_adaptation_cost=sum(item.adaptation_cost for item in results) / count,
    )


__all__ = ["AdaptationSeedResult", "PrivateModelAdaptationStudy", "run_private_model_adaptation_study"]
