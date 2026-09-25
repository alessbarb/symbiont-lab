"""Low-level opaque sensorimotor forward model for Embodiment v2."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Mapping


class EvidenceProvenance(StrEnum):
    EXPERIENCED = "experienced"
    IMAGINED = "imagined"


@dataclass(frozen=True, slots=True)
class PredictionResidual:
    percept_id: str
    predicted_delta: float
    observed_delta: float
    error: float
    tick: int
    provenance: EvidenceProvenance = EvidenceProvenance.EXPERIENCED


class SensorimotorDynamicsModel:
    """Bounded learned mapping from opaque activations to perceptual deltas.

    This is deliberately a small online model rather than a commitment to a
    particular ML architecture.  It supplies the canonical low-level forward
    model interface required by body-schema revision, adaptation and future
    internal simulation.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        learning_rate: float = 0.08,
        max_relations: int = 8192,
    ) -> None:
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be in (0,1]")
        if max_relations < 1:
            raise ValueError("max_relations must be positive")
        self.learning_rate = float(learning_rate)
        self.max_relations = int(max_relations)
        self._weights: dict[tuple[str, str], float] = {}
        self._support: dict[tuple[str, str], int] = {}
        self._last_prediction: dict[str, float] = {}
        self._last_activations: dict[str, float] = {}
        self._error_ema = 0.0
        self._error_count = 0

    def predict(
        self,
        activations: Mapping[str, float],
        percept_ids: tuple[str, ...] | list[str],
    ) -> dict[str, float]:
        result: dict[str, float] = {}
        for percept_id in percept_ids:
            result[percept_id] = sum(
                float(level) * self._weights.get((actuator_id, percept_id), 0.0)
                for actuator_id, level in activations.items()
            )
        self._last_prediction = dict(result)
        self._last_activations = {
            str(key): float(value) for key, value in activations.items()
        }
        return result

    def observe(
        self,
        observed_deltas: Mapping[str, float],
        *,
        tick: int,
        activations: Mapping[str, float] | None = None,
        provenance: EvidenceProvenance = EvidenceProvenance.EXPERIENCED,
    ) -> tuple[PredictionResidual, ...]:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        acts = (
            {str(key): float(value) for key, value in activations.items()}
            if activations is not None
            else self._last_activations
        )
        residuals: list[PredictionResidual] = []
        for percept_id, observed in observed_deltas.items():
            observed_value = float(observed)
            predicted = float(self._last_prediction.get(percept_id, 0.0))
            signed_error = observed_value - predicted
            residuals.append(
                PredictionResidual(
                    percept_id=str(percept_id),
                    predicted_delta=predicted,
                    observed_delta=observed_value,
                    error=abs(signed_error),
                    tick=tick,
                    provenance=provenance,
                )
            )
            if provenance is not EvidenceProvenance.EXPERIENCED:
                continue
            self._error_count += 1
            alpha = min(0.1, 1.0 / self._error_count)
            self._error_ema += alpha * (abs(signed_error) - self._error_ema)
            for actuator_id, level in acts.items():
                if abs(level) <= 1e-9:
                    continue
                key = (actuator_id, str(percept_id))
                current = self._weights.get(key, 0.0)
                self._weights[key] = current + self.learning_rate * signed_error * level
                self._support[key] = min(65535, self._support.get(key, 0) + 1)
        self._enforce_bound()
        return tuple(residuals)

    def _enforce_bound(self) -> None:
        if len(self._weights) <= self.max_relations:
            return
        retained = sorted(
            self._weights,
            key=lambda key: (-self._support.get(key, 0), key[0], key[1]),
        )[: self.max_relations]
        keep = set(retained)
        self._weights = {key: value for key, value in self._weights.items() if key in keep}
        self._support = {key: value for key, value in self._support.items() if key in keep}

    @property
    def mean_prediction_error(self) -> float:
        return self._error_ema if self._error_count else 0.0

    @property
    def relation_count(self) -> int:
        return len(self._weights)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "learning_rate": self.learning_rate,
            "max_relations": self.max_relations,
            "error_ema": self._error_ema,
            "error_count": self._error_count,
            "relations": [
                {
                    "actuator_id": actuator_id,
                    "percept_id": percept_id,
                    "weight": weight,
                    "support": self._support.get((actuator_id, percept_id), 0),
                }
                for (actuator_id, percept_id), weight in sorted(self._weights.items())
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "SensorimotorDynamicsModel":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported sensorimotor dynamics checkpoint")
        obj = cls(
            learning_rate=float(payload.get("learning_rate", 0.08)),
            max_relations=int(payload.get("max_relations", 8192)),
        )
        obj._error_ema = float(payload.get("error_ema", 0.0))
        obj._error_count = int(payload.get("error_count", 0))
        if not math.isfinite(obj._error_ema) or obj._error_ema < 0.0 or obj._error_count < 0:
            raise ValueError("invalid sensorimotor dynamics error state")
        raw = payload.get("relations", [])
        if not isinstance(raw, list) or len(raw) > obj.max_relations:
            raise ValueError("invalid or unbounded sensorimotor dynamics relations")
        for item in raw:
            if not isinstance(item, Mapping):
                raise ValueError("invalid sensorimotor dynamics relation")
            key = (str(item["actuator_id"]), str(item["percept_id"]))
            weight = float(item["weight"])
            support = int(item.get("support", 0))
            if not math.isfinite(weight) or support < 0:
                raise ValueError("invalid sensorimotor dynamics relation values")
            obj._weights[key] = weight
            obj._support[key] = support
        return obj


__all__ = [
    "EvidenceProvenance",
    "PredictionResidual",
    "SensorimotorDynamicsModel",
]
