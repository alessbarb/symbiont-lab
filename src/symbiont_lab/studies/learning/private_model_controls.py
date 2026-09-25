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
from symbiont_lab.modeling import (
    TrainingConfig,
    encode_corpus,
    remap_encoded_corpus,
    train_private_model,
)
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model


@dataclass(frozen=True, slots=True)
class PrivateModelControlSeedResult:
    seed: int
    specificity_margin: float
    own_a_loss: float
    cross_a_loss: float
    own_b_loss: float
    cross_b_loss: float
    original_symbol_loss: float
    stale_remap_loss: float
    retrained_remap_loss: float
    remap_disruption: float
    remap_recovery_gap: float
    pre_shift_loss: float
    post_shift_stale_loss: float
    post_shift_retrained_loss: float
    regime_degradation: float
    regime_recovery: float


@dataclass(frozen=True, slots=True)
class PrivateModelControlsStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[PrivateModelControlSeedResult, ...]
    mean_specificity_margin: float
    mean_remap_disruption: float
    mean_remap_recovery_gap: float
    mean_regime_degradation: float
    mean_regime_recovery: float

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
    *,
    organism_id: str,
    seed: int,
    ticks: int,
    rule: int,
) -> tuple[ExperienceRecord, ...]:
    """Generate an opaque controlled lifetime with no organism/rule label in model-facing tokens."""

    records: list[ExperienceRecord] = []
    phase = seed % 5
    for tick in range(ticks):
        left = (phase + tick) % 5
        right = (phase * 3 + tick * 2) % 7
        action = (left + right + tick) % 3
        if rule == 0:
            outcome = (left * 2 + right + action) % 5
        elif rule == 1:
            outcome = (left + right * 2 + action * 3 + 1) % 5
        else:
            raise ValueError("unsupported controlled rule")
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


def _cross_loss(training, encoded) -> float:
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


def run_private_model_controls_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> PrivateModelControlsStudy:
    """Strong post-utility controls for individual specificity, opaque-symbol invariance and regime adaptation.

    The protocol deliberately uses only GRU-v1. Architecture comparison is already
    covered by learning.private-model-utility; these controls test the scientific
    interpretation of learned structure rather than model-family selection.
    """

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 64 <= ticks <= 4096:
        raise ValueError("ticks must be within [64, 4096]")

    results: list[PrivateModelControlSeedResult] = []
    for seed in normalized:
        # A. Individual specificity. Both individuals expose the same opaque
        # vocabulary but live under different hidden contingencies. Identity is
        # never a model-facing token.
        corpus_a = build_training_corpus(
            _history(organism_id=f"specific-a-{seed}", seed=seed, ticks=ticks, rule=0)
        )
        corpus_b = build_training_corpus(
            _history(organism_id=f"specific-b-{seed}", seed=seed, ticks=ticks, rule=1)
        )
        shared_tokenizer = NativeTokenizer.from_records((*corpus_a.train, *corpus_b.train))
        encoded_a = encode_corpus(corpus_a, shared_tokenizer, context_window=32)
        encoded_b = encode_corpus(corpus_b, shared_tokenizer, context_window=32)
        trained_a = _train(
            corpus=corpus_a,
            encoded=encoded_a,
            tokenizer_hash=shared_tokenizer.tokenizer_hash,
            seed=seed,
        )
        trained_b = _train(
            corpus=corpus_b,
            encoded=encoded_b,
            tokenizer_hash=shared_tokenizer.tokenizer_hash,
            seed=seed + 10_000,
        )
        own_a = _loss(trained_a, encoded_a)
        cross_a = _cross_loss(trained_a, encoded_b)
        own_b = _loss(trained_b, encoded_b)
        cross_b = _cross_loss(trained_b, encoded_a)
        specificity_margin = ((cross_a - own_a) + (cross_b - own_b)) / 2.0

        # B. Opaque symbol remapping. A stale model should be disrupted by a
        # consistent permutation of non-reserved ids, while a model retrained on
        # the permuted experience should recover comparable predictive utility.
        original_symbol_loss = own_a
        remapped = remap_encoded_corpus(encoded_a, seed=seed + 20_000)
        stale_remap_loss = _cross_loss(trained_a, remapped)
        remap_training = _train(
            corpus=corpus_a, encoded=remapped, tokenizer_hash=remapped.tokenizer_hash, seed=seed
        )
        retrained_remap_loss = _loss(remap_training, remapped)
        remap_disruption = stale_remap_loss - original_symbol_loss
        remap_recovery_gap = retrained_remap_loss - original_symbol_loss

        # C. Regime shift. Train on one contingency, expose the frozen model to
        # another, then train a fresh successor from post-shift experience. The
        # experiment measures degradation and recovery without changing labels or
        # evaluator knowledge available to the model.
        post_corpus = build_training_corpus(
            _history(organism_id=f"regime-{seed}", seed=seed, ticks=ticks, rule=1)
        )
        pre_corpus = build_training_corpus(
            _history(organism_id=f"regime-{seed}", seed=seed, ticks=ticks, rule=0)
        )
        regime_tokenizer = NativeTokenizer.from_records((*pre_corpus.train, *post_corpus.train))
        pre_encoded = encode_corpus(pre_corpus, regime_tokenizer, context_window=32)
        post_encoded = encode_corpus(post_corpus, regime_tokenizer, context_window=32)
        pre_training = _train(
            corpus=pre_corpus,
            encoded=pre_encoded,
            tokenizer_hash=regime_tokenizer.tokenizer_hash,
            seed=seed,
        )
        post_training = _train(
            corpus=post_corpus,
            encoded=post_encoded,
            tokenizer_hash=regime_tokenizer.tokenizer_hash,
            seed=seed + 30_000,
        )
        pre_shift_loss = _loss(pre_training, pre_encoded)
        post_shift_stale_loss = _cross_loss(pre_training, post_encoded)
        post_shift_retrained_loss = _loss(post_training, post_encoded)
        regime_degradation = post_shift_stale_loss - pre_shift_loss
        regime_recovery = post_shift_stale_loss - post_shift_retrained_loss

        results.append(
            PrivateModelControlSeedResult(
                seed=seed,
                specificity_margin=specificity_margin,
                own_a_loss=own_a,
                cross_a_loss=cross_a,
                own_b_loss=own_b,
                cross_b_loss=cross_b,
                original_symbol_loss=original_symbol_loss,
                stale_remap_loss=stale_remap_loss,
                retrained_remap_loss=retrained_remap_loss,
                remap_disruption=remap_disruption,
                remap_recovery_gap=remap_recovery_gap,
                pre_shift_loss=pre_shift_loss,
                post_shift_stale_loss=post_shift_stale_loss,
                post_shift_retrained_loss=post_shift_retrained_loss,
                regime_degradation=regime_degradation,
                regime_recovery=regime_recovery,
            )
        )

    count = len(results)
    return PrivateModelControlsStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        mean_specificity_margin=sum(item.specificity_margin for item in results) / count,
        mean_remap_disruption=sum(item.remap_disruption for item in results) / count,
        mean_remap_recovery_gap=sum(item.remap_recovery_gap for item in results) / count,
        mean_regime_degradation=sum(item.regime_degradation for item in results) / count,
        mean_regime_recovery=sum(item.regime_recovery for item in results) / count,
    )


__all__ = [
    "PrivateModelControlSeedResult",
    "PrivateModelControlsStudy",
    "run_private_model_controls_study",
]
