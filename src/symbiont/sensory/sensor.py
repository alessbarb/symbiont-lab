from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any

from .transduction import TransductionKind


class MaturityState(StrEnum):
    NASCENT = "nascent"
    IMMATURE = "immature"
    ESTABLISHED = "established"
    SPECIALISED = "specialised"
    DEGRADED = "degraded"


@dataclass(slots=True)
class SensorState:
    sensor_id: str
    modality_id: str
    source_ids: tuple[str, ...]
    cognitive_name: str
    transduction: TransductionKind = TransductionKind.IDENTITY
    gain: float = 1.0
    decay: float = 0.8
    threshold: float = 0.0
    born_tick: int = 0
    age_ticks: int = 0
    maturity: MaturityState = MaturityState.NASCENT
    health: float = 1.0
    confidence: float = 0.0
    utility: float = 0.0
    redundancy: float = 0.0
    acquisition_cost: float = 0.0
    transduction_cost: float = 0.001
    parent_sensor_ids: tuple[str, ...] = ()
    structural_revision: int = 0
    # Transient state is deliberately not checkpointed.
    previous_input: float | None = None
    integrator: float = 0.0
    last_output: float | None = None
    previous_output: float | None = None
    output_abs_ewma: float = 0.0
    output_delta_ewma: float = 0.0
    output_observations: int = 0
    utility_observations: int = 0

    def __post_init__(self) -> None:
        if not self.sensor_id or any(ch.isspace() for ch in self.sensor_id):
            raise ValueError("sensor_id must be a non-empty token")
        if not self.modality_id or not self.source_ids or not self.cognitive_name:
            raise ValueError("sensor modality, sources and cognitive_name are required")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("sensor source_ids must be unique")
        for name, value in (
            ("gain", self.gain),
            ("decay", self.decay),
            ("threshold", self.threshold),
            ("health", self.health),
            ("confidence", self.confidence),
            ("utility", self.utility),
            ("redundancy", self.redundancy),
            ("acquisition_cost", self.acquisition_cost),
            ("transduction_cost", self.transduction_cost),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if not 0.0 < self.gain <= 8.0 or not 0.0 <= self.decay <= 1.0:
            raise ValueError("sensor gain/decay outside bounds")
        for name in ("health", "confidence", "utility", "redundancy"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.acquisition_cost < 0.0 or self.transduction_cost <= 0.0:
            raise ValueError("sensor costs must be non-negative/positive")

    def advance_maturity(self) -> None:
        if self.health < 0.25:
            self.maturity = MaturityState.DEGRADED
        elif self.age_ticks >= 64 and self.transduction is not TransductionKind.IDENTITY:
            self.maturity = MaturityState.SPECIALISED
        elif self.age_ticks >= 16:
            self.maturity = MaturityState.ESTABLISHED
        elif self.age_ticks >= 4:
            self.maturity = MaturityState.IMMATURE
        else:
            self.maturity = MaturityState.NASCENT

    def observe_quality(self, quality_score: float) -> None:
        score = max(0.0, min(1.0, float(quality_score)))
        self.health = 0.9 * self.health + 0.1 * score
        maturity_factor = min(1.0, self.age_ticks / 16.0)
        self.confidence = max(0.0, min(1.0, 0.7 * self.health + 0.3 * maturity_factor))

    def observe_output(self, value: float) -> None:
        if not math.isfinite(float(value)):
            return
        value = float(value)
        magnitude = min(1_000_000.0, abs(value))
        delta = 0.0 if self.previous_output is None else min(1_000_000.0, abs(value - self.previous_output))
        self.output_observations += 1
        alpha = 1.0 if self.output_observations == 1 else 0.1
        self.output_abs_ewma = (1.0 - alpha) * self.output_abs_ewma + alpha * magnitude
        self.output_delta_ewma = (1.0 - alpha) * self.output_delta_ewma + alpha * delta
        self.previous_output = value
    def observe_utility(self, contribution: float) -> None:
        contribution = max(0.0, min(1.0, float(contribution)))
        self.utility_observations += 1
        alpha = 0.2 if self.utility_observations > 1 else 1.0
        self.utility = (1.0 - alpha) * self.utility + alpha * contribution

    def checkpoint(self) -> dict[str, Any]:
        """Durable phenotype without raw/transient signal state."""
        return {
            "sensor_id": self.sensor_id,
            "modality_id": self.modality_id,
            "source_ids": list(self.source_ids),
            "cognitive_name": self.cognitive_name,
            "transduction": self.transduction.value,
            "gain": self.gain,
            "decay": self.decay,
            "threshold": self.threshold,
            "born_tick": self.born_tick,
            "age_ticks": self.age_ticks,
            "maturity": self.maturity.value,
            "health": self.health,
            "confidence": self.confidence,
            "utility": self.utility,
            "redundancy": self.redundancy,
            "acquisition_cost": self.acquisition_cost,
            "transduction_cost": self.transduction_cost,
            "parent_sensor_ids": list(self.parent_sensor_ids),
            "structural_revision": self.structural_revision,
            "output_abs_ewma": self.output_abs_ewma,
            "output_delta_ewma": self.output_delta_ewma,
            "output_observations": self.output_observations,
            "utility_observations": self.utility_observations,
        }

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> "SensorState":
        return cls(
            sensor_id=str(payload["sensor_id"]),
            modality_id=str(payload["modality_id"]),
            source_ids=tuple(str(v) for v in payload["source_ids"]),
            cognitive_name=str(payload["cognitive_name"]),
            transduction=TransductionKind(payload.get("transduction", "identity")),
            gain=float(payload.get("gain", 1.0)),
            decay=float(payload.get("decay", 0.8)),
            threshold=float(payload.get("threshold", 0.0)),
            born_tick=int(payload.get("born_tick", 0)),
            age_ticks=int(payload.get("age_ticks", 0)),
            maturity=MaturityState(payload.get("maturity", "nascent")),
            health=float(payload.get("health", 1.0)),
            confidence=float(payload.get("confidence", 0.0)),
            utility=float(payload.get("utility", 0.0)),
            redundancy=float(payload.get("redundancy", 0.0)),
            acquisition_cost=float(payload.get("acquisition_cost", 0.0)),
            transduction_cost=float(payload.get("transduction_cost", 0.001)),
            parent_sensor_ids=tuple(str(v) for v in payload.get("parent_sensor_ids", ())),
            structural_revision=int(payload.get("structural_revision", 0)),
            output_abs_ewma=float(payload.get("output_abs_ewma", 0.0)),
            output_delta_ewma=float(payload.get("output_delta_ewma", 0.0)),
            output_observations=int(payload.get("output_observations", 0)),
            utility_observations=int(payload.get("utility_observations", 0)),
        )
