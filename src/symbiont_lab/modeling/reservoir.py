from __future__ import annotations

import math
import random
from typing import Sequence

from symbiont.modeling.temporal import TemporalPrediction, TemporalResourceUsage


class SparseEchoStateRegressor:
    """Small fixed recurrent reservoir with online normalized-LMS readout.

    The reservoir is immutable after construction. Only the linear readout is
    adapted. This intentionally avoids the O(N^2) covariance matrix of full RLS
    while retaining a recurrent continuous state for temporal experiments.
    """

    def __init__(
        self,
        *,
        input_dim: int,
        output_dim: int,
        reservoir_size: int = 64,
        connectivity: float = 0.1,
        spectral_scale: float = 0.9,
        leak_rate: float = 0.3,
        learning_rate: float = 0.1,
        seed: int = 0,
        mechanism_id: str = "esn-nlms-v1",
    ) -> None:
        for name, value, low, high in (
            ("input_dim", input_dim, 1, 256),
            ("output_dim", output_dim, 1, 256),
            ("reservoir_size", reservoir_size, 4, 2048),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name} must be within [{low}, {high}]")
        for name, value, low, high in (
            ("connectivity", connectivity, 0.001, 1.0),
            ("spectral_scale", spectral_scale, 0.01, 1.5),
            ("leak_rate", leak_rate, 0.001, 1.0),
            ("learning_rate", learning_rate, 1e-6, 1.0),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not low <= float(value) <= high
            ):
                raise ValueError(f"{name} must be within [{low}, {high}]")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        if not isinstance(mechanism_id, str) or not mechanism_id or len(mechanism_id) > 128:
            raise ValueError("mechanism_id must be bounded")

        self._input_dim = input_dim
        self._output_dim = output_dim
        self._reservoir_size = reservoir_size
        self._leak_rate = float(leak_rate)
        self._learning_rate = float(learning_rate)
        self._mechanism_id = mechanism_id
        self._state = [0.0] * reservoir_size
        self._last_input = [0.0] * input_dim
        self._observations = 0
        self._updates = 0

        rng = random.Random(seed)
        self._input_weights = [
            [rng.uniform(-1.0, 1.0) for _ in range(input_dim + 1)]
            for _ in range(reservoir_size)
        ]

        # Sparse recurrent rows: (source_index, weight). Row-normalizing by the
        # absolute sum gives a deterministic bounded recurrence. spectral_scale
        # is therefore a safe recurrence scale, not a claim of exact spectral
        # radius measurement.
        recurrent: list[list[tuple[int, float]]] = []
        for _ in range(reservoir_size):
            row: list[tuple[int, float]] = []
            for source in range(reservoir_size):
                if rng.random() < connectivity:
                    row.append((source, rng.uniform(-1.0, 1.0)))
            if not row:
                source = rng.randrange(reservoir_size)
                row.append((source, rng.uniform(-1.0, 1.0)))
            norm = sum(abs(weight) for _, weight in row)
            recurrent.append(
                [
                    (source, float(spectral_scale) * weight / max(norm, 1e-12))
                    for source, weight in row
                ]
            )
        self._recurrent = recurrent

        feature_dim = 1 + input_dim + reservoir_size
        self._readout = [
            [0.0] * feature_dim
            for _ in range(output_dim)
        ]

    @property
    def mechanism_id(self) -> str:
        return self._mechanism_id

    def _validate_vector(self, values: Sequence[float], *, size: int, name: str) -> list[float]:
        if len(values) != size:
            raise ValueError(f"{name} must contain {size} values")
        resolved: list[float] = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} values must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{name} values must be finite")
            resolved.append(numeric)
        return resolved

    def _advance(self, input_values: Sequence[float]) -> list[float]:
        values = self._validate_vector(input_values, size=self._input_dim, name="observation")
        previous = self._state
        updated: list[float] = []
        for index in range(self._reservoir_size):
            input_row = self._input_weights[index]
            drive = input_row[0]
            for offset, value in enumerate(values, start=1):
                drive += input_row[offset] * value
            recurrent_drive = sum(
                weight * previous[source]
                for source, weight in self._recurrent[index]
            )
            candidate = math.tanh(drive + recurrent_drive)
            updated.append(
                (1.0 - self._leak_rate) * previous[index]
                + self._leak_rate * candidate
            )
        self._state = updated
        self._last_input = values
        self._observations += 1
        return updated

    def _features(self) -> list[float]:
        return [1.0, *self._last_input, *self._state]

    def observe(self, observation: Sequence[float]) -> None:
        self._advance(observation)

    def predict(self, *, horizon: int = 1) -> TemporalPrediction[tuple[float, ...]] | None:
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon != 1:
            raise ValueError("ESN challenger currently supports horizon=1 only")
        if self._observations == 0:
            return None
        features = self._features()
        output = tuple(
            sum(weight * feature for weight, feature in zip(row, features))
            for row in self._readout
        )
        # Continuous regression has no calibrated probability. Confidence is
        # intentionally left neutral rather than fabricating calibration.
        return TemporalPrediction(
            mechanism_id=self.mechanism_id,
            horizon=1,
            value=output,
            confidence=0.0,
        )

    def learn(self, target: Sequence[float]) -> tuple[float, ...]:
        """Apply one normalized-LMS update against the current reservoir state."""
        if self._observations == 0:
            raise ValueError("observe must be called before learn")
        expected = self._validate_vector(target, size=self._output_dim, name="target")
        prediction = self.predict()
        assert prediction is not None
        errors = tuple(
            expected[index] - prediction.value[index]
            for index in range(self._output_dim)
        )
        features = self._features()
        denominator = 1e-9 + sum(feature * feature for feature in features)
        step = self._learning_rate / denominator
        for output_index, error in enumerate(errors):
            row = self._readout[output_index]
            for feature_index, feature in enumerate(features):
                row[feature_index] += step * error * feature
        self._updates += 1
        return errors

    def resource_usage(self) -> TemporalResourceUsage:
        recurrent_values = sum(len(row) for row in self._recurrent)
        input_values = self._reservoir_size * (self._input_dim + 1)
        readout_values = self._output_dim * (
            1 + self._input_dim + self._reservoir_size
        )
        return TemporalResourceUsage(
            state_values=self._reservoir_size + self._input_dim,
            learned_values=readout_values,
            observations=self._observations,
            updates=self._updates,
        )

    @property
    def fixed_values(self) -> int:
        """Number of immutable reservoir/input parameters for cost accounting."""
        return (
            sum(len(row) for row in self._recurrent)
            + self._reservoir_size * (self._input_dim + 1)
        )


__all__ = ["SparseEchoStateRegressor"]
