from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import EpistemicStatus, ExperienceRecord, SourceKind, build_training_corpus
from symbiont_lab.modeling import PromotionPolicy, TrainingConfig, run_model_family_study


@dataclass(frozen=True, slots=True)
class PrivateModelUtilityStudy:
    seeds: tuple[int, ...]
    ticks: int
    gru_mean_test_loss: float
    transformer_mean_test_loss: float
    gru_mean_gain_over_trivial: float
    transformer_mean_gain_over_trivial: float
    gru_promotions: int
    transformer_promotions: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _life_history(*, seed: int, ticks: int) -> tuple[ExperienceRecord, ...]:
    # Opaque controlled world: outcome depends on a two-signal state and an
    # action. No semantic class label is present in the model-facing record.
    records: list[ExperienceRecord] = []
    phase = seed % 5
    for tick in range(ticks):
        left = (phase + tick) % 5
        right = (phase * 3 + tick * 2) % 7
        action = (left + right + tick) % 3
        outcome = (left * 2 + right + action) % 5
        records.append(ExperienceRecord(
            record_id=f"episode.{seed}.{tick}",
            organism_id=f"study-organism-{seed}",
            tick_class=tick,
            context_tokens=(f"sense.{left}", f"sense.{right}"),
            action_token=f"action.{action}",
            outcome_tokens=(f"outcome.{outcome}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.{seed}.{tick}",),
            confidence_class=7,
            source_kind=SourceKind.ACTION_OUTCOME,
        ))
    return tuple(records)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Normalize declarative TOML lists and direct tuple callers identically."""
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


def run_private_model_utility_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> PrivateModelUtilityStudy:
    """Experiment A: verify private models can beat trivial held-out baselines."""

    normalized_seeds = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 48 <= ticks <= 4096:
        raise ValueError("ticks must be within [48, 4096]")

    gru_losses: list[float] = []
    transformer_losses: list[float] = []
    gru_gains: list[float] = []
    transformer_gains: list[float] = []
    gru_promotions = 0
    transformer_promotions = 0

    for seed in normalized_seeds:
        corpus = build_training_corpus(_life_history(seed=seed, ticks=ticks))
        result = run_model_family_study(
            corpus,
            seed=seed,
            context_window=32,
            epochs=8,
            steps=512,
            training_config=TrainingConfig(batch_size=16, patience=3),
            promotion_policy=PromotionPolicy(minimum_log_loss_gain=0.01),
        )
        by_arch = {item.architecture_id.value: item for item in result.families}
        gru = by_arch["gru-v1"]
        transformer = by_arch["transformer-v1"]
        gru_losses.append(gru.evaluation.candidate.mean_log_loss)
        transformer_losses.append(transformer.evaluation.candidate.mean_log_loss)
        gru_gains.append(gru.evaluation.gain_over_trivial)
        transformer_gains.append(transformer.evaluation.gain_over_trivial)
        gru_promotions += int(gru.promotion.promote)
        transformer_promotions += int(transformer.promotion.promote)

    count = len(normalized_seeds)
    return PrivateModelUtilityStudy(
        seeds=normalized_seeds,
        ticks=ticks,
        gru_mean_test_loss=sum(gru_losses) / count,
        transformer_mean_test_loss=sum(transformer_losses) / count,
        gru_mean_gain_over_trivial=sum(gru_gains) / count,
        transformer_mean_gain_over_trivial=sum(transformer_gains) / count,
        gru_promotions=gru_promotions,
        transformer_promotions=transformer_promotions,
    )


__all__ = ["PrivateModelUtilityStudy", "run_private_model_utility_study"]
