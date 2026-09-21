from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import EpistemicStatus, ExperienceRecord, SourceKind, build_training_corpus
from symbiont_lab.modeling import PromotionPolicy, TrainingConfig, run_model_family_study


@dataclass(frozen=True, slots=True)
class PrivateModelSeedResult:
    seed: int
    gru_test_loss: float
    gru_gain_over_trivial: float
    gru_promoted: bool
    gru_promotion_reason: str
    transformer_test_loss: float
    transformer_gain_over_trivial: float
    transformer_gain_over_gru: float
    transformer_promoted: bool
    transformer_promotion_reason: str
    vomm_test_loss: float
    vomm_gain_over_trivial: float
    decayed_vomm_test_loss: float
    decayed_vomm_gain_over_trivial: float


@dataclass(frozen=True, slots=True)
class PrivateModelUtilityStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[PrivateModelSeedResult, ...]
    gru_mean_test_loss: float
    transformer_mean_test_loss: float
    gru_mean_gain_over_trivial: float
    transformer_mean_gain_over_trivial: float
    transformer_mean_gain_over_gru: float
    gru_promotions: int
    transformer_promotions: int
    vomm_mean_test_loss: float
    decayed_vomm_mean_test_loss: float
    vomm_mean_gain_over_trivial: float
    decayed_vomm_mean_gain_over_trivial: float

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
    """Experiment A: verify private models can beat trivial held-out baselines.

    Aggregate metrics are retained for compatibility, but every preregistered seed
    is preserved explicitly so a positive mean cannot conceal a failed replicate.
    """

    normalized_seeds = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 48 <= ticks <= 4096:
        raise ValueError("ticks must be within [48, 4096]")

    seed_results: list[PrivateModelSeedResult] = []

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
        if len(result.temporal_challengers) != 2:
            raise RuntimeError("private-model study requires stationary and decayed VOMM challengers")
        stationary_vomm, decayed_vomm = result.temporal_challengers
        best_trivial = gru.evaluation.best_trivial_loss
        seed_results.append(PrivateModelSeedResult(
            seed=seed,
            gru_test_loss=gru.evaluation.candidate.mean_log_loss,
            gru_gain_over_trivial=gru.evaluation.gain_over_trivial,
            gru_promoted=gru.promotion.promote,
            gru_promotion_reason=gru.promotion.reason,
            transformer_test_loss=transformer.evaluation.candidate.mean_log_loss,
            transformer_gain_over_trivial=transformer.evaluation.gain_over_trivial,
            transformer_gain_over_gru=(
                gru.evaluation.candidate.mean_log_loss
                - transformer.evaluation.candidate.mean_log_loss
            ),
            transformer_promoted=transformer.promotion.promote,
            transformer_promotion_reason=transformer.promotion.reason,
            vomm_test_loss=stationary_vomm.mean_log_loss,
            vomm_gain_over_trivial=best_trivial - stationary_vomm.mean_log_loss,
            decayed_vomm_test_loss=decayed_vomm.mean_log_loss,
            decayed_vomm_gain_over_trivial=best_trivial - decayed_vomm.mean_log_loss,
        ))

    count = len(seed_results)
    return PrivateModelUtilityStudy(
        seeds=normalized_seeds,
        ticks=ticks,
        per_seed=tuple(seed_results),
        gru_mean_test_loss=sum(item.gru_test_loss for item in seed_results) / count,
        transformer_mean_test_loss=sum(item.transformer_test_loss for item in seed_results) / count,
        gru_mean_gain_over_trivial=sum(item.gru_gain_over_trivial for item in seed_results) / count,
        transformer_mean_gain_over_trivial=sum(item.transformer_gain_over_trivial for item in seed_results) / count,
        transformer_mean_gain_over_gru=sum(item.transformer_gain_over_gru for item in seed_results) / count,
        gru_promotions=sum(int(item.gru_promoted) for item in seed_results),
        transformer_promotions=sum(int(item.transformer_promoted) for item in seed_results),
        vomm_mean_test_loss=sum(item.vomm_test_loss for item in seed_results) / count,
        decayed_vomm_mean_test_loss=sum(item.decayed_vomm_test_loss for item in seed_results) / count,
        vomm_mean_gain_over_trivial=sum(item.vomm_gain_over_trivial for item in seed_results) / count,
        decayed_vomm_mean_gain_over_trivial=sum(
            item.decayed_vomm_gain_over_trivial for item in seed_results
        ) / count,
    )


__all__ = [
    "PrivateModelSeedResult",
    "PrivateModelUtilityStudy",
    "run_private_model_utility_study",
]
