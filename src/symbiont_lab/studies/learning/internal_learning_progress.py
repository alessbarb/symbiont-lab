from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import (
    ModeledOrganismRuntime,
    ModelObjective,
    ModelTrainingAuthority,
    TrainingRequest,
)
from symbiont_lab.modeling import TrainingConfig, encode_corpus, train_private_model
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model

from .adaptive_replay_matched_control import _normalize_seeds, _transition_history
from .replay_pressure_curve import PRESSURES, _budget_for_pressure


@dataclass(frozen=True, slots=True)
class LearningProgressDose:
    pressure: float
    epochs: int
    steps: int
    internal_validation_loss: float
    evaluator_test_loss: float


@dataclass(frozen=True, slots=True)
class LearningProgressSeedResult:
    seed: int
    doses: tuple[LearningProgressDose, ...]
    interval_sign_agreement: int
    interval_count: int
    pearson_gain_correlation: float


@dataclass(frozen=True, slots=True)
class LearningProgressStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[LearningProgressSeedResult, ...]
    mean_sign_agreement_fraction: float
    mean_pearson_gain_correlation: float
    positive_correlation_seeds: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _request(plan, pressure: float) -> TrainingRequest:
    epochs, steps = _budget_for_pressure(pressure)
    base = plan.request
    return TrainingRequest(
        organism_id=base.organism_id,
        corpus_hash=base.corpus_hash,
        tokenizer_hash=base.tokenizer_hash,
        architecture_id=base.architecture_id,
        objective=ModelObjective.NEXT_TOKEN,
        seed=base.seed,
        context_window=base.context_window,
        requested_parameters=base.requested_parameters,
        requested_epochs=epochs,
        requested_steps=steps,
        created_tick_class=base.created_tick_class,
        autonomous_stopping=False,
    )


def _train_dose(*, request: TrainingRequest, corpus, tokenizer) -> LearningProgressDose:
    encoded = encode_corpus(corpus, tokenizer, context_window=request.context_window)
    training = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(),
        config=TrainingConfig(batch_size=16, patience=64),
        device="cpu",
    )
    model = load_artifact_model(
        training.artifact,
        vocab_size=encoded.vocab_size,
        pad_id=encoded.pad_id,
        device="cpu",
    )
    test = evaluate_outcome_model(
        model,
        encoded.test,
        pad_id=encoded.pad_id,
        context_window=request.context_window,
    )
    return LearningProgressDose(
        pressure=0.0,
        epochs=training.epochs_completed,
        steps=training.steps_completed,
        internal_validation_loss=training.validation_metrics.mean_log_loss,
        evaluator_test_loss=test.mean_log_loss,
    )


def _pearson(xs: tuple[float, ...], ys: tuple[float, ...]) -> float:
    if len(xs) != len(ys) or not xs:
        raise ValueError("correlation inputs must be non-empty and matched")
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = tuple(value - mx for value in xs)
    dy = tuple(value - my for value in ys)
    denom = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    if denom <= 1e-15:
        return 0.0
    return sum(a * b for a, b in zip(dx, dy)) / denom


def run_internal_learning_progress_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> LearningProgressStudy:
    """L7.6: validate private validation loss as an organism-owned progress signal.

    The organism may observe validation loss because it is computed exclusively
    from its own observed causal experience reserved from replay updates.
    Evaluator test loss is never exposed to the organism and is used only here.
    """

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 96 <= ticks <= 4096:
        raise ValueError("ticks must be within [96, 4096]")

    results: list[LearningProgressSeedResult] = []
    for seed in normalized:
        organism_id = f"internal-progress-{seed}"
        runtime = ModeledOrganismRuntime(
            organism_id=organism_id,
            bootstrap_semantic_senses=False,
            discover_senses=False,
        )
        for record in _transition_history(
            organism_id=organism_id,
            seed=seed,
            ticks=ticks,
        ):
            runtime.record_experience(record)
        plan = runtime.autonomous_private_learning_plan()
        if plan is None:
            raise RuntimeError("L7.6 history failed to trigger replay plan")

        doses: list[LearningProgressDose] = []
        for pressure in PRESSURES:
            request = _request(plan, pressure)
            measured = _train_dose(
                request=request,
                corpus=plan.corpus,
                tokenizer=plan.tokenizer,
            )
            doses.append(
                LearningProgressDose(
                    pressure=pressure,
                    epochs=measured.epochs,
                    steps=measured.steps,
                    internal_validation_loss=measured.internal_validation_loss,
                    evaluator_test_loss=measured.evaluator_test_loss,
                )
            )

        internal_gains = tuple(
            left.internal_validation_loss - right.internal_validation_loss
            for left, right in zip(doses, doses[1:])
        )
        test_gains = tuple(
            left.evaluator_test_loss - right.evaluator_test_loss
            for left, right in zip(doses, doses[1:])
        )
        sign_agreement = sum(
            (internal > 0.0) == (external > 0.0)
            for internal, external in zip(internal_gains, test_gains)
        )
        results.append(
            LearningProgressSeedResult(
                seed=seed,
                doses=tuple(doses),
                interval_sign_agreement=sign_agreement,
                interval_count=len(internal_gains),
                pearson_gain_correlation=_pearson(internal_gains, test_gains),
            )
        )

    total_intervals = sum(item.interval_count for item in results)
    total_agreement = sum(item.interval_sign_agreement for item in results)
    return LearningProgressStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        mean_sign_agreement_fraction=total_agreement / total_intervals,
        mean_pearson_gain_correlation=sum(item.pearson_gain_correlation for item in results)
        / len(results),
        positive_correlation_seeds=sum(item.pearson_gain_correlation > 0.0 for item in results),
    )


__all__ = [
    "LearningProgressDose",
    "LearningProgressSeedResult",
    "LearningProgressStudy",
    "run_internal_learning_progress_study",
]
