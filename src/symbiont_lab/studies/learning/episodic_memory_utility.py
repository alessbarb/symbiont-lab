"""Scientific assay for state-conditioned utility of episodic experience memory.

The apparatus is observer-only. It builds a memory from a training prefix and
scores held-out observed transitions. No score, label or selected winner is
fed back into the organism.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Iterable
import random

from symbiont.cognition.limits import KernelLimits
from symbiont.modeling.episodic import EpisodicExperienceMemory
from symbiont.modeling.experience import EpistemicStatus, ExperienceRecord, SourceKind


def _causal(records: Iterable[ExperienceRecord]) -> tuple[ExperienceRecord, ...]:
    return tuple(
        record
        for record in records
        if record.record_id.startswith("transition.")
        and record.epistemic_status is EpistemicStatus.OBSERVED
        and record.source_kind is not SourceKind.MODEL
        and record.outcome_tokens
    )


def _top(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return min(counter, key=lambda token: (-counter[token], token))


@dataclass(frozen=True, slots=True)
class EpisodicUtilityReport:
    train_records: int
    test_records: int
    memory_coverage: float
    memory_top1_accuracy: float
    action_only_top1_accuracy: float
    global_top1_accuracy: float
    memory_log_loss: float
    action_only_log_loss: float
    global_log_loss: float
    state_conditioned_gain_vs_action_only: float
    state_conditioned_gain_vs_global: float


def _smoothed_probability(counter: Counter[str], token: str, vocabulary: set[str]) -> float:
    # Laplace smoothing keeps the assay finite and treats every arm equally.
    total = sum(counter.values())
    width = max(1, len(vocabulary))
    return (counter.get(token, 0) + 1.0) / (total + width)


def evaluate_episodic_predictive_utility(
    train: Iterable[ExperienceRecord],
    test: Iterable[ExperienceRecord],
    *,
    organism_id: str,
    kernel_limits: KernelLimits | None = None,
) -> EpisodicUtilityReport:
    """Evaluate held-out outcome prediction from lived state/action context."""
    training = _causal(train)
    testing = _causal(test)
    memory = EpisodicExperienceMemory(organism_id, kernel_limits=kernel_limits)

    action_counts: dict[str | None, Counter[str]] = defaultdict(Counter)
    global_counts: Counter[str] = Counter()
    vocabulary: set[str] = set()
    for record in training:
        memory.observe(record)
        for outcome in record.outcome_tokens:
            action_counts[record.action_token][outcome] += 1
            global_counts[outcome] += 1
            vocabulary.add(outcome)
    for record in testing:
        vocabulary.update(record.outcome_tokens)
    memory.flush()

    memory_correct = 0
    action_correct = 0
    global_correct = 0
    covered = 0
    memory_loss = 0.0
    action_loss = 0.0
    global_loss = 0.0

    global_prediction = _top(global_counts)
    for record in testing:
        truth = record.outcome_tokens[0]

        prediction = memory.predict(
            record.context_tokens,
            action_token=record.action_token,
        )
        if prediction is not None and prediction.predicted_outcomes:
            covered += 1
            predicted = prediction.predicted_outcomes[0]
            memory_correct += int(predicted == truth)
            # Convert confidence into a conservative categorical probability.
            p = prediction.confidence if predicted == truth else (
                (1.0 - prediction.confidence) / max(1, len(vocabulary) - 1)
            )
            memory_loss += -math.log(max(1e-12, min(1.0, p)))
        else:
            # No retrieval is a real miss, not silently replaced by a baseline.
            memory_loss += -math.log(1.0 / max(1, len(vocabulary)))

        action_counter = action_counts.get(record.action_token, Counter())
        action_prediction = _top(action_counter)
        action_correct += int(action_prediction == truth)
        action_loss += -math.log(
            max(1e-12, _smoothed_probability(action_counter, truth, vocabulary))
        )

        global_correct += int(global_prediction == truth)
        global_loss += -math.log(
            max(1e-12, _smoothed_probability(global_counts, truth, vocabulary))
        )

    count = len(testing)
    if count == 0:
        return EpisodicUtilityReport(
            train_records=len(training),
            test_records=0,
            memory_coverage=0.0,
            memory_top1_accuracy=0.0,
            action_only_top1_accuracy=0.0,
            global_top1_accuracy=0.0,
            memory_log_loss=0.0,
            action_only_log_loss=0.0,
            global_log_loss=0.0,
            state_conditioned_gain_vs_action_only=0.0,
            state_conditioned_gain_vs_global=0.0,
        )

    memory_accuracy = memory_correct / count
    action_accuracy = action_correct / count
    global_accuracy = global_correct / count
    return EpisodicUtilityReport(
        train_records=len(training),
        test_records=count,
        memory_coverage=covered / count,
        memory_top1_accuracy=memory_accuracy,
        action_only_top1_accuracy=action_accuracy,
        global_top1_accuracy=global_accuracy,
        memory_log_loss=memory_loss / count,
        action_only_log_loss=action_loss / count,
        global_log_loss=global_loss / count,
        state_conditioned_gain_vs_action_only=memory_accuracy - action_accuracy,
        state_conditioned_gain_vs_global=memory_accuracy - global_accuracy,
    )




@dataclass(frozen=True, slots=True)
class EpisodicUtilitySeedResult:
    seed: int
    report: EpisodicUtilityReport

    def as_dict(self) -> dict[str, object]:
        return {"seed": self.seed, **asdict(self.report)}


@dataclass(frozen=True, slots=True)
class EpisodicUtilityStudy:
    seeds: tuple[int, ...]
    ticks: int
    results: tuple[EpisodicUtilitySeedResult, ...]
    mean_state_conditioned_gain_vs_action_only: float
    mean_state_conditioned_gain_vs_global: float
    mean_memory_coverage: float

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "ticks": self.ticks,
            "mean_state_conditioned_gain_vs_action_only": (
                self.mean_state_conditioned_gain_vs_action_only
            ),
            "mean_state_conditioned_gain_vs_global": (
                self.mean_state_conditioned_gain_vs_global
            ),
            "mean_memory_coverage": self.mean_memory_coverage,
            "results": [result.as_dict() for result in self.results],
        }


def _study_records(
    *,
    seed: int,
    ticks: int,
    organism_id: str,
) -> tuple[ExperienceRecord, ...]:
    """Build an evaluator-owned ambiguity challenge with no reward semantics.

    The same opaque action has different consequences in two opaque contexts.
    Small independent context noise prevents exact string memorisation from
    being sufficient while preserving the state-conditioned contingency.
    """
    rng = random.Random(seed)
    records: list[ExperienceRecord] = []
    for index in range(ticks):
        regime = index % 2
        state = f"state.regime.{regime}"
        noise = f"state.noise.{rng.randrange(8)}"
        outcome = f"outcome.regime.{regime}"
        records.append(
            ExperienceRecord(
                record_id=f"transition.study.{seed}.{index:08d}",
                organism_id=organism_id,
                tick_class=index * 4,
                context_tokens=("sense.shared", state, noise),
                action_token="action.shared",
                outcome_tokens=(outcome,),
                epistemic_status=EpistemicStatus.OBSERVED,
                evidence_refs=(f"evidence.study.{seed}.{index}",),
                confidence_class=7,
                source_kind=SourceKind.ACTION_OUTCOME,
            )
        )
    return tuple(records)


def run_episodic_memory_utility_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
    ticks: int = 256,
) -> EpisodicUtilityStudy:
    """Replicated held-out state-conditioning challenge.

    This is apparatus-only and never feeds labels or scores into a live
    organism. Temporal splitting keeps future observations out of training.
    """
    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple:
        raise ValueError("seeds must not be empty")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 64:
        raise ValueError("ticks must be an integer >= 64")

    results: list[EpisodicUtilitySeedResult] = []
    for seed in seed_tuple:
        organism_id = f"episodic-study-{seed}"
        records = _study_records(
            seed=seed,
            ticks=ticks,
            organism_id=organism_id,
        )
        split = max(32, int(len(records) * 0.70))
        split = min(split, len(records) - 16)
        report = evaluate_episodic_predictive_utility(
            records[:split],
            records[split:],
            organism_id=organism_id,
        )
        results.append(EpisodicUtilitySeedResult(seed=seed, report=report))

    count = len(results)
    return EpisodicUtilityStudy(
        seeds=seed_tuple,
        ticks=ticks,
        results=tuple(results),
        mean_state_conditioned_gain_vs_action_only=sum(
            result.report.state_conditioned_gain_vs_action_only
            for result in results
        ) / count,
        mean_state_conditioned_gain_vs_global=sum(
            result.report.state_conditioned_gain_vs_global
            for result in results
        ) / count,
        mean_memory_coverage=sum(
            result.report.memory_coverage for result in results
        ) / count,
    )

__all__ = [
    "EpisodicUtilityReport",
    "EpisodicUtilitySeedResult",
    "EpisodicUtilityStudy",
    "evaluate_episodic_predictive_utility",
    "run_episodic_memory_utility_study",
]
