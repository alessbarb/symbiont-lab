"""Scientific assay for state-conditioned utility of episodic experience memory.

The apparatus is observer-only. It builds a memory from a training prefix and
scores held-out observed transitions. No score, label or selected winner is
fed back into the organism.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from typing import Iterable

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


__all__ = [
    "EpisodicUtilityReport",
    "evaluate_episodic_predictive_utility",
]
