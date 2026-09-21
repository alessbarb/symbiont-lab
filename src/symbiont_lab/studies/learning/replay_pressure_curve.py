from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import ModelObjective, ModelTrainingAuthority, TrainingRequest
from symbiont_lab.modeling import TrainingConfig, encode_corpus, train_private_model
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model
from .adaptive_replay_matched_control import _normalize_seeds, _transition_history
from symbiont.modeling import ModeledOrganismRuntime


PRESSURES = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True, slots=True)
class ReplayDose:
    pressure: float
    epochs: int
    steps: int
    test_loss: float
    accuracy: float


@dataclass(frozen=True, slots=True)
class ReplayPressureSeedResult:
    seed: int
    doses: tuple[ReplayDose, ...]
    monotonic_nonincreasing_loss: bool
    saturation_gain_last_quarter: float


@dataclass(frozen=True, slots=True)
class ReplayPressureCurveStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[ReplayPressureSeedResult, ...]
    monotonic_loss_seeds: int
    mean_saturation_gain_last_quarter: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _budget_for_pressure(pressure: float) -> tuple[int, int]:
    if pressure not in PRESSURES:
        raise ValueError("unsupported preregistered pressure")
    return 2 + round(6 * pressure), 12 + round(36 * pressure)


def _request_at_pressure(plan, pressure: float) -> TrainingRequest:
    epochs, steps = _budget_for_pressure(pressure)
    request = plan.request
    return TrainingRequest(
        organism_id=request.organism_id,
        corpus_hash=request.corpus_hash,
        tokenizer_hash=request.tokenizer_hash,
        architecture_id=request.architecture_id,
        objective=ModelObjective.NEXT_TOKEN,
        seed=request.seed,
        context_window=request.context_window,
        requested_parameters=request.requested_parameters,
        requested_epochs=epochs,
        requested_steps=steps,
        created_tick_class=request.created_tick_class,
        parent_model_id=request.parent_model_id,
        adaptation_reason=request.adaptation_reason,
    )


def _score(*, request: TrainingRequest, corpus, tokenizer):
    encoded = encode_corpus(corpus, tokenizer, context_window=request.context_window)
    training = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(),
        config=TrainingConfig(batch_size=16, patience=8),
        device="cpu",
    )
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
        context_window=request.context_window,
    )


def run_replay_pressure_curve_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> ReplayPressureCurveStudy:
    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 96 <= ticks <= 4096:
        raise ValueError("ticks must be within [96, 4096]")

    results: list[ReplayPressureSeedResult] = []
    for seed in normalized:
        organism_id = f"replay-pressure-{seed}"
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
            raise RuntimeError("pressure-curve history failed to trigger replay plan")

        doses: list[ReplayDose] = []
        for pressure in PRESSURES:
            request = _request_at_pressure(plan, pressure)
            metrics = _score(
                request=request,
                corpus=plan.corpus,
                tokenizer=plan.tokenizer,
            )
            doses.append(ReplayDose(
                pressure=pressure,
                epochs=request.requested_epochs,
                steps=request.requested_steps,
                test_loss=metrics.mean_log_loss,
                accuracy=metrics.accuracy,
            ))

        monotonic = all(
            right.test_loss <= left.test_loss + 1e-12
            for left, right in zip(doses, doses[1:])
        )
        results.append(ReplayPressureSeedResult(
            seed=seed,
            doses=tuple(doses),
            monotonic_nonincreasing_loss=monotonic,
            saturation_gain_last_quarter=doses[-2].test_loss - doses[-1].test_loss,
        ))

    return ReplayPressureCurveStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        monotonic_loss_seeds=sum(item.monotonic_nonincreasing_loss for item in results),
        mean_saturation_gain_last_quarter=(
            sum(item.saturation_gain_last_quarter for item in results) / len(results)
        ),
    )


__all__ = [
    "PRESSURES",
    "ReplayDose",
    "ReplayPressureSeedResult",
    "ReplayPressureCurveStudy",
    "run_replay_pressure_curve_study",
]
