from __future__ import annotations

from collections import defaultdict, deque
import math

from symbiont.modeling.temporal import TemporalPrediction, TemporalResourceUsage


class DecayedVariableOrderMarkov:
    """Online discrete temporal challenger with variable-order contexts.

    This is deliberately *not* labelled CTW: it uses decayed Dirichlet-smoothed
    context counts and longest-supported-context prediction. It provides a
    transparent non-neural baseline for testing whether exact CTW/ACTW is worth
    the additional implementation complexity.
    """

    def __init__(
        self,
        *,
        max_order: int = 8,
        decay: float = 1.0,
        smoothing: float = 0.5,
        mechanism_id: str = "vomm-decayed-v1",
    ) -> None:
        if isinstance(max_order, bool) or not isinstance(max_order, int) or not 1 <= max_order <= 64:
            raise ValueError("max_order must be within [1, 64]")
        if (
            isinstance(decay, bool)
            or not isinstance(decay, (int, float))
            or not math.isfinite(float(decay))
            or not 0.0 < float(decay) <= 1.0
        ):
            raise ValueError("decay must be within (0, 1]")
        if (
            isinstance(smoothing, bool)
            or not isinstance(smoothing, (int, float))
            or not math.isfinite(float(smoothing))
            or float(smoothing) <= 0.0
        ):
            raise ValueError("smoothing must be positive")
        if not isinstance(mechanism_id, str) or not mechanism_id or len(mechanism_id) > 128:
            raise ValueError("mechanism_id must be bounded")

        self._max_order = max_order
        self._decay = float(decay)
        self._smoothing = float(smoothing)
        self._mechanism_id = mechanism_id
        self._history: deque[int] = deque(maxlen=max_order)
        self._counts: dict[tuple[int, ...], dict[int, float]] = defaultdict(dict)
        self._vocabulary: set[int] = set()
        self._observations = 0
        self._updates = 0

    @property
    def mechanism_id(self) -> str:
        return self._mechanism_id

    def _decay_context(self, context: tuple[int, ...]) -> None:
        if self._decay >= 1.0:
            return
        bucket = self._counts.get(context)
        if not bucket:
            return
        dead: list[int] = []
        for symbol, value in bucket.items():
            updated = value * self._decay
            if updated < 1e-9:
                dead.append(symbol)
            else:
                bucket[symbol] = updated
        for symbol in dead:
            del bucket[symbol]
        if not bucket:
            self._counts.pop(context, None)

    def observe(self, observation: int) -> None:
        if isinstance(observation, bool) or not isinstance(observation, int) or observation < 0:
            raise ValueError("observation must be a non-negative integer symbol")

        history = tuple(self._history)
        self._vocabulary.add(observation)
        for order in range(0, min(len(history), self._max_order) + 1):
            context = history[-order:] if order else ()
            self._decay_context(context)
            bucket = self._counts.setdefault(context, {})
            bucket[observation] = bucket.get(observation, 0.0) + 1.0
            self._updates += 1

        self._history.append(observation)
        self._observations += 1

    def distribution(self) -> dict[int, float]:
        if not self._vocabulary:
            return {}
        history = tuple(self._history)
        vocabulary = tuple(sorted(self._vocabulary))

        chosen: dict[int, float] | None = None
        for order in range(min(len(history), self._max_order), -1, -1):
            context = history[-order:] if order else ()
            bucket = self._counts.get(context)
            if bucket and sum(bucket.values()) > 0.0:
                chosen = bucket
                break
        if chosen is None:
            probability = 1.0 / len(vocabulary)
            return {symbol: probability for symbol in vocabulary}

        denominator = sum(chosen.values()) + self._smoothing * len(vocabulary)
        return {
            symbol: (chosen.get(symbol, 0.0) + self._smoothing) / denominator
            for symbol in vocabulary
        }

    def predict(self, *, horizon: int = 1) -> TemporalPrediction[int] | None:
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon != 1:
            raise ValueError("vomm challenger currently supports horizon=1 only")
        distribution = self.distribution()
        if not distribution:
            return None
        symbol = min(
            distribution,
            key=lambda candidate: (-distribution[candidate], candidate),
        )
        return TemporalPrediction(
            mechanism_id=self.mechanism_id,
            horizon=1,
            value=symbol,
            confidence=distribution[symbol],
        )

    def resource_usage(self) -> TemporalResourceUsage:
        learned = sum(len(bucket) for bucket in self._counts.values())
        return TemporalResourceUsage(
            state_values=len(self._history),
            learned_values=learned,
            observations=self._observations,
            updates=self._updates,
        )


__all__ = ["DecayedVariableOrderMarkov"]
