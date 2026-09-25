from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class AutonomousStoppingArm:
    name: str
    requested_epochs: int
    requested_steps: int
    epochs_completed: int
    steps_completed: int
    internal_validation_loss: float
    evaluator_test_loss: float


@dataclass(frozen=True, slots=True)
class AutonomousStoppingSeedResult:
    seed: int
    minimum: AutonomousStoppingArm
    autonomous: AutonomousStoppingArm
    maximum: AutonomousStoppingArm
    compute_saved_fraction: float
    retained_gain_fraction: float
    passes_efficiency_gate: bool


@dataclass(frozen=True, slots=True)
class AutonomousStoppingStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[AutonomousStoppingSeedResult, ...]
    passing_seeds: int
    mean_compute_saved_fraction: float
    mean_retained_gain_fraction: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _request(
    plan,
    *,
    epochs: int,
    steps: int,
    autonomous_stopping: bool,
) -> TrainingRequest:
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
        autonomous_stopping=autonomous_stopping,
        requested_patience=2,
        requested_min_validation_gain=0.005,
    )


def _run_arm(*, name: str, request: TrainingRequest, corpus, tokenizer) -> AutonomousStoppingArm:
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
    return AutonomousStoppingArm(
        name=name,
        requested_epochs=request.requested_epochs,
        requested_steps=request.requested_steps,
        epochs_completed=training.epochs_completed,
        steps_completed=training.steps_completed,
        internal_validation_loss=training.validation_metrics.mean_log_loss,
        evaluator_test_loss=test.mean_log_loss,
    )


def run_autonomous_replay_stopping_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> AutonomousStoppingStudy:
    """L7.8 final gate for organism-owned replay stopping.

    Minimum and maximum arms disable autonomous stopping. The autonomous arm
    receives the same maximum ceiling but may stop early using only private
    validation loss. Evaluator test loss remains inaccessible to the policy.
    """

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 96 <= ticks <= 4096:
        raise ValueError("ticks must be within [96, 4096]")

    results: list[AutonomousStoppingSeedResult] = []
    for seed in normalized:
        organism_id = f"autonomous-stopping-{seed}"
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
            raise RuntimeError("L7.8 history failed to trigger replay plan")

        minimum = _run_arm(
            name="minimum",
            request=_request(plan, epochs=2, steps=12, autonomous_stopping=False),
            corpus=plan.corpus,
            tokenizer=plan.tokenizer,
        )
        maximum = _run_arm(
            name="maximum",
            request=_request(plan, epochs=8, steps=48, autonomous_stopping=False),
            corpus=plan.corpus,
            tokenizer=plan.tokenizer,
        )
        autonomous = _run_arm(
            name="autonomous",
            request=_request(plan, epochs=8, steps=48, autonomous_stopping=True),
            corpus=plan.corpus,
            tokenizer=plan.tokenizer,
        )

        max_gain = minimum.evaluator_test_loss - maximum.evaluator_test_loss
        autonomous_gain = minimum.evaluator_test_loss - autonomous.evaluator_test_loss
        retained = autonomous_gain / max_gain if max_gain > 1e-12 else 1.0
        saved = 1.0 - autonomous.steps_completed / max(1, maximum.steps_completed)
        passed = (
            autonomous.steps_completed < maximum.steps_completed
            and retained >= 0.90
            and autonomous.evaluator_test_loss <= minimum.evaluator_test_loss
        )
        results.append(
            AutonomousStoppingSeedResult(
                seed=seed,
                minimum=minimum,
                autonomous=autonomous,
                maximum=maximum,
                compute_saved_fraction=saved,
                retained_gain_fraction=retained,
                passes_efficiency_gate=passed,
            )
        )

    return AutonomousStoppingStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        passing_seeds=sum(item.passes_efficiency_gate for item in results),
        mean_compute_saved_fraction=sum(item.compute_saved_fraction for item in results)
        / len(results),
        mean_retained_gain_fraction=sum(item.retained_gain_fraction for item in results)
        / len(results),
    )


__all__ = [
    "AutonomousStoppingArm",
    "AutonomousStoppingSeedResult",
    "AutonomousStoppingStudy",
    "run_autonomous_replay_stopping_study",
]
