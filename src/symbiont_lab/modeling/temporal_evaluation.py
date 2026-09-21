from __future__ import annotations

from dataclasses import dataclass
import math

from symbiont.modeling.temporal import TemporalResourceUsage

from .context_tree import DecayedVariableOrderMarkov
from .dataset import EncodedSplit


@dataclass(frozen=True, slots=True)
class DiscreteTemporalMetrics:
    mechanism_id: str
    mean_log_loss: float
    accuracy: float
    predictions: int
    resource_usage: TemporalResourceUsage

    def __post_init__(self) -> None:
        if not isinstance(self.mechanism_id, str) or not self.mechanism_id:
            raise ValueError("mechanism_id must be non-empty")
        if not math.isfinite(self.mean_log_loss) or self.mean_log_loss < 0.0:
            raise ValueError("mean_log_loss must be finite and non-negative")
        if not math.isfinite(self.accuracy) or not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("accuracy must be within [0, 1]")
        if isinstance(self.predictions, bool) or not isinstance(self.predictions, int) or self.predictions < 1:
            raise ValueError("predictions must be positive")


def _fit_sequences(
    model: DecayedVariableOrderMarkov,
    split: EncodedSplit,
) -> None:
    for sequence in split.sequences:
        model.reset_context()
        for token in sequence:
            model.observe(token)


def evaluate_vomm_challenger(
    train: EncodedSplit,
    test: EncodedSplit,
    *,
    max_order: int = 8,
    decay: float = 1.0,
    smoothing: float = 0.5,
) -> DiscreteTemporalMetrics:
    """Held-out next-token evaluation on the same outcome positions as SLM.

    Test tokens advance context but never update learned counts, keeping the
    held-out comparison free of online adaptation leakage.
    """
    model = DecayedVariableOrderMarkov(
        max_order=max_order,
        decay=decay,
        smoothing=smoothing,
    )
    _fit_sequences(model, train)

    total_loss = 0.0
    correct = 0
    predictions = 0
    epsilon = 1e-12

    for sequence, outcome_positions in zip(
        test.sequences,
        test.outcome_target_positions,
    ):
        model.reset_context()
        positions = set(outcome_positions)
        for index, token in enumerate(sequence):
            model.condition(token)
            if index not in positions or index + 1 >= len(sequence):
                continue

            target = sequence[index + 1]
            distribution = model.distribution()
            probability = distribution.get(target, 0.0)
            total_loss -= math.log(max(probability, epsilon))
            if distribution:
                predicted = min(
                    distribution,
                    key=lambda candidate: (-distribution[candidate], candidate),
                )
                correct += int(predicted == target)
            predictions += 1

    if predictions < 1:
        raise ValueError("test split contains no outcome targets")

    return DiscreteTemporalMetrics(
        mechanism_id=model.mechanism_id,
        mean_log_loss=total_loss / predictions,
        accuracy=correct / predictions,
        predictions=predictions,
        resource_usage=model.resource_usage(),
    )


__all__ = [
    "DiscreteTemporalMetrics",
    "evaluate_vomm_challenger",
]
