from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .dataset import EncodedSplit


@dataclass(frozen=True, slots=True)
class BaselineMetrics:
    name: str
    mean_log_loss: float
    accuracy: float
    predictions: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("baseline name must be non-empty")
        if not math.isfinite(self.mean_log_loss) or self.mean_log_loss < 0.0:
            raise ValueError("mean_log_loss must be finite and non-negative")
        if not math.isfinite(self.accuracy) or not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("accuracy must be within [0, 1]")
        if (
            isinstance(self.predictions, bool)
            or not isinstance(self.predictions, int)
            or self.predictions < 1
        ):
            raise ValueError("predictions must be positive")


def _outcome_transitions(split: EncodedSplit):
    for sequence, positions in zip(split.sequences, split.outcome_target_positions):
        for position in positions:
            yield sequence[position], sequence[position + 1]


def evaluate_uniform_baseline(split: EncodedSplit, *, vocab_size: int) -> BaselineMetrics:
    if isinstance(vocab_size, bool) or not isinstance(vocab_size, int) or vocab_size < 2:
        raise ValueError("vocab_size must be at least 2")
    count = split.outcome_predictions
    if count < 1:
        raise ValueError("split contains no outcome targets")
    return BaselineMetrics("uniform", math.log(vocab_size), 0.0, count)


def evaluate_persistence_baseline(split: EncodedSplit, *, vocab_size: int) -> BaselineMetrics:
    epsilon = 1e-9
    loss = 0.0
    correct = 0
    count = 0
    for current, target in _outcome_transitions(split):
        probability = (1.0 - epsilon) if target == current else epsilon / max(1, vocab_size - 1)
        loss -= math.log(max(probability, 1e-12))
        correct += int(target == current)
        count += 1
    if count < 1:
        raise ValueError("split contains no outcome targets")
    return BaselineMetrics("persistence", loss / count, correct / count, count)


def evaluate_frequency_baseline(
    train: EncodedSplit, test: EncodedSplit, *, vocab_size: int
) -> BaselineMetrics:
    counts: Counter[int] = Counter(target for _, target in _outcome_transitions(train))
    total = sum(counts.values())
    if total < 1:
        raise ValueError("training split contains no outcome targets")
    smoothing = 1.0
    denominator = total + smoothing * vocab_size
    most_common = min(range(vocab_size), key=lambda token: (-counts[token], token))
    loss = 0.0
    correct = 0
    observations = 0
    for _, target in _outcome_transitions(test):
        probability = (counts[target] + smoothing) / denominator
        loss -= math.log(max(probability, 1e-12))
        correct += int(target == most_common)
        observations += 1
    if observations < 1:
        raise ValueError("test split contains no outcome targets")
    return BaselineMetrics("frequency", loss / observations, correct / observations, observations)
