from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
import random

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
    PromotionPolicy,
    TrainingConfig,
    encode_corpus,
    evaluate_candidate,
    train_private_model,
)


@dataclass(frozen=True, slots=True)
class TemporalControlCondition:
    condition: str
    candidate_loss: float
    gain_over_trivial: float
    promoted: bool
    promotion_reason: str
    best_baseline: str
    best_baseline_loss: float


@dataclass(frozen=True, slots=True)
class TemporalPrivateModelControlSeedResult:
    seed: int
    causal: TemporalControlCondition
    action_shuffled: TemporalControlCondition
    next_state_shuffled: TemporalControlCondition
    no_action: TemporalControlCondition
    causal_gain_margin_over_best_control: float
    all_controls_below_causal: bool


@dataclass(frozen=True, slots=True)
class TemporalPrivateModelControlsStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[TemporalPrivateModelControlSeedResult, ...]
    all_seeds_causal_beats_controls: bool
    mean_causal_gain_margin: float

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


def temporal_history(*, seed: int, ticks: int) -> tuple[ExperienceRecord, ...]:
    """Opaque controlled transitions where action is necessary for next state.

    Model-facing records have the same causal shape used by Physics3D:
    state(t) + action(t) -> observed state change(t+1).  No body/anatomy label
    or evaluator-only causal variable enters the tokens.
    """

    rng = random.Random(seed)
    state = seed % 8
    records: list[ExperienceRecord] = []
    for tick in range(ticks):
        action = rng.randrange(4)
        next_state = (state * 3 + action * 5 + 1) % 8
        delta = (next_state - state) % 8
        records.append(ExperienceRecord(
            record_id=f"transition.control.{seed}.{tick}",
            organism_id=f"temporal-control-{seed}",
            tick_class=tick,
            context_tokens=(
                "sense.opaque",
                f"state.sense.opaque.level.{state}",
            ),
            action_token=f"action.motor.{action}",
            outcome_tokens=(f"outcome.sense.opaque.delta.{delta}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.control.{seed}.{tick}",),
            confidence_class=7,
            source_kind=SourceKind.ACTION_OUTCOME,
        ))
        state = next_state
    return tuple(records)


def _permute(
    records: tuple[ExperienceRecord, ...],
    *,
    seed: int,
    field: str,
) -> tuple[ExperienceRecord, ...]:
    rng = random.Random(seed)
    indices = list(range(len(records)))
    rng.shuffle(indices)
    if len(indices) > 1 and all(index == value for index, value in enumerate(indices)):
        indices = indices[1:] + indices[:1]

    if field == "action":
        values = [records[index].action_token for index in indices]
        return tuple(
            replace(record, action_token=value)
            for record, value in zip(records, values)
        )
    if field == "outcome":
        values = [records[index].outcome_tokens for index in indices]
        return tuple(
            replace(record, outcome_tokens=value)
            for record, value in zip(records, values)
        )
    raise ValueError("field must be action or outcome")


def temporal_controls(
    records: tuple[ExperienceRecord, ...],
    *,
    seed: int,
) -> dict[str, tuple[ExperienceRecord, ...]]:
    if len(records) < 3:
        raise ValueError("temporal controls require at least 3 records")
    return {
        "causal": records,
        "action_shuffled": _permute(records, seed=seed + 10_001, field="action"),
        "next_state_shuffled": _permute(records, seed=seed + 20_003, field="outcome"),
        "no_action": tuple(replace(record, action_token=None) for record in records),
    }


def _train_condition(
    name: str,
    records: tuple[ExperienceRecord, ...],
    *,
    seed: int,
) -> TemporalControlCondition:
    corpus = build_training_corpus(records)
    tokenizer = NativeTokenizer.from_records(corpus.train)
    encoded = encode_corpus(corpus, tokenizer, context_window=32)
    request = TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=6,
        requested_steps=256,
        created_tick_class=corpus.manifest.last_tick_class,
    )
    training = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(),
        config=TrainingConfig(batch_size=16, patience=3),
        device="cpu",
    )
    evaluation, decision = evaluate_candidate(
        training.artifact,
        encoded,
        policy=PromotionPolicy(minimum_log_loss_gain=0.01),
        device="cpu",
    )
    baselines = {
        "uniform": evaluation.uniform.mean_log_loss,
        "frequency": evaluation.frequency.mean_log_loss,
        "persistence": evaluation.persistence.mean_log_loss,
    }
    best_baseline = min(baselines, key=baselines.get)
    return TemporalControlCondition(
        condition=name,
        candidate_loss=evaluation.candidate.mean_log_loss,
        gain_over_trivial=evaluation.gain_over_trivial,
        promoted=decision.promote,
        promotion_reason=decision.reason,
        best_baseline=best_baseline,
        best_baseline_loss=baselines[best_baseline],
    )


def run_temporal_private_model_controls_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 256,
) -> TemporalPrivateModelControlsStudy:
    """Test whether temporal SLM utility depends on genuine action→next-state structure."""

    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 96 <= ticks <= 4096:
        raise ValueError("ticks must be within [96, 4096]")

    results: list[TemporalPrivateModelControlSeedResult] = []
    for seed in normalized:
        base = temporal_history(seed=seed, ticks=ticks)
        controls = temporal_controls(base, seed=seed)
        measured = {
            name: _train_condition(
                name,
                records,
                seed=seed + offset,
            )
            for offset, (name, records) in enumerate(controls.items())
        }
        causal = measured["causal"]
        control_gains = (
            measured["action_shuffled"].gain_over_trivial,
            measured["next_state_shuffled"].gain_over_trivial,
            measured["no_action"].gain_over_trivial,
        )
        best_control = max(control_gains)
        results.append(TemporalPrivateModelControlSeedResult(
            seed=seed,
            causal=causal,
            action_shuffled=measured["action_shuffled"],
            next_state_shuffled=measured["next_state_shuffled"],
            no_action=measured["no_action"],
            causal_gain_margin_over_best_control=causal.gain_over_trivial - best_control,
            all_controls_below_causal=all(
                causal.gain_over_trivial > gain for gain in control_gains
            ),
        ))

    return TemporalPrivateModelControlsStudy(
        seeds=normalized,
        ticks=ticks,
        per_seed=tuple(results),
        all_seeds_causal_beats_controls=all(
            item.all_controls_below_causal for item in results
        ),
        mean_causal_gain_margin=(
            sum(item.causal_gain_margin_over_best_control for item in results)
            / len(results)
        ),
    )


__all__ = [
    "TemporalControlCondition",
    "TemporalPrivateModelControlSeedResult",
    "TemporalPrivateModelControlsStudy",
    "run_temporal_private_model_controls_study",
    "temporal_controls",
    "temporal_history",
]
