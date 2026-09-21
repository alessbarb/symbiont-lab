from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.modeling import (
    ArchitectureId,
    ExperienceRecord,
    EpistemicStatus,
    ModelObjective,
    ModelTrainingAuthority,
    ModeledOrganismRuntime,
    SourceKind,
    TrainingRequest,
)
from symbiont_lab.modeling import TrainingConfig, encode_corpus, train_private_model
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model


@dataclass(frozen=True, slots=True)
class AdaptiveReplaySeedResult:
    seed: int
    transitions: int
    replay_pressure: float
    adaptive_epochs: int
    adaptive_steps: int
    control_epochs: int
    control_steps: int
    adaptive_test_loss: float
    control_test_loss: float
    adaptive_accuracy: float
    control_accuracy: float
    loss_gain: float
    accuracy_gain: float


@dataclass(frozen=True, slots=True)
class AdaptiveReplayMatchedControlStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[AdaptiveReplaySeedResult, ...]
    mean_loss_gain: float
    mean_accuracy_gain: float
    positive_loss_seeds: int
    positive_accuracy_seeds: int

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


def _transition_history(
    *,
    organism_id: str,
    seed: int,
    ticks: int,
) -> tuple[ExperienceRecord, ...]:
    """Opaque causal history shared byte-for-byte by both replay arms."""
    phase = seed % 11
    records: list[ExperienceRecord] = []
    for tick in range(ticks):
        left = (phase + tick * 2) % 7
        right = (phase * 3 + tick * 5) % 9
        action = (left + right + tick) % 4
        outcome = (left * 3 + right * 2 + action + (tick // 13)) % 7
        records.append(ExperienceRecord(
            record_id=f"transition.l73.{seed}.{tick}",
            organism_id=organism_id,
            tick_class=tick,
            context_tokens=(f"sense.{left}", f"sense.{right}"),
            action_token=f"action.{action}",
            outcome_tokens=(f"outcome.{outcome}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.l73.{seed}.{tick}",),
            confidence_class=7,
            source_kind=SourceKind.ACTION_OUTCOME,
        ))
    return tuple(records)


def _matched_control_request(plan) -> TrainingRequest:
    """Ablate adaptive replay amount while preserving every other request field."""
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
        requested_epochs=2,
        requested_steps=12,
        created_tick_class=request.created_tick_class,
        parent_model_id=request.parent_model_id,
        adaptation_reason=request.adaptation_reason,
    )


def _train_and_score(*, request: TrainingRequest, corpus, tokenizer):
    encoded = encode_corpus(
        corpus,
        tokenizer,
        context_window=request.context_window,
    )
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
    metrics = evaluate_outcome_model(
        model,
        encoded.test,
        pad_id=encoded.pad_id,
        context_window=request.context_window,
    )
    return metrics


def run_adaptive_replay_matched_control_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> AdaptiveReplayMatchedControlStudy:
    """L7.3: isolate the causal effect of adaptive replay compute.

    Each seed produces one organism-owned causal history and one endogenous L7.2
    training plan. Treatment and control receive the exact same history, corpus,
    tokenizer, architecture, objective, parameter ceiling, seed and test split.
    Only the replay compute budget differs: treatment uses the organism-authored
    request; control clamps the request to the constitutional minimum 2 epochs /
    12 steps. Evaluator metrics are read only after both arms finish and never
    feed back into either arm.
    """

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 96 <= ticks <= 4096:
        raise ValueError("ticks must be within [96, 4096]")

    results: list[AdaptiveReplaySeedResult] = []
    for seed in normalized:
        organism_id = f"adaptive-replay-{seed}"
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
            raise RuntimeError("L7.3 history failed to trigger an autonomous replay plan")

        adaptive_request = plan.request
        control_request = _matched_control_request(plan)

        adaptive = _train_and_score(
            request=adaptive_request,
            corpus=plan.corpus,
            tokenizer=plan.tokenizer,
        )
        control = _train_and_score(
            request=control_request,
            corpus=plan.corpus,
            tokenizer=plan.tokenizer,
        )

        results.append(AdaptiveReplaySeedResult(
            seed=seed,
            transitions=ticks,
            replay_pressure=plan.replay_pressure,
            adaptive_epochs=adaptive_request.requested_epochs,
            adaptive_steps=adaptive_request.requested_steps,
            control_epochs=control_request.requested_epochs,
            control_steps=control_request.requested_steps,
            adaptive_test_loss=adaptive.mean_log_loss,
            control_test_loss=control.mean_log_loss,
            adaptive_accuracy=adaptive.accuracy,
            control_accuracy=control.accuracy,
            loss_gain=control.mean_log_loss - adaptive.mean_log_loss,
            accuracy_gain=adaptive.accuracy - control.accuracy,
        ))

    count = len(results)
    return AdaptiveReplayMatchedControlStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        mean_loss_gain=sum(item.loss_gain for item in results) / count,
        mean_accuracy_gain=sum(item.accuracy_gain for item in results) / count,
        positive_loss_seeds=sum(item.loss_gain > 0.0 for item in results),
        positive_accuracy_seeds=sum(item.accuracy_gain > 0.0 for item in results),
    )


__all__ = [
    "AdaptiveReplaySeedResult",
    "AdaptiveReplayMatchedControlStudy",
    "run_adaptive_replay_matched_control_study",
]
