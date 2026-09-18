from __future__ import annotations

from dataclasses import dataclass
import math

from .transduction import TransductionKind


@dataclass(slots=True, frozen=True)
class SensoryModality:
    """A substrate family, never a human semantic sense label."""

    modality_id: str
    allowed_transductions: tuple[TransductionKind, ...]
    max_inputs: int
    temporal_capacity: int
    base_cost: float

    def __post_init__(self) -> None:
        if not isinstance(self.modality_id, str) or not self.modality_id or any(ch.isspace() for ch in self.modality_id):
            raise ValueError("modality_id must be a non-empty token")
        if not self.allowed_transductions or any(not isinstance(item, TransductionKind) for item in self.allowed_transductions):
            raise ValueError("a modality must allow valid transduction kinds")
        if len(set(self.allowed_transductions)) != len(self.allowed_transductions):
            raise ValueError("modality transductions must be unique")
        if isinstance(self.max_inputs, bool) or not isinstance(self.max_inputs, int) or self.max_inputs <= 0:
            raise ValueError("max_inputs must be a positive integer")
        if isinstance(self.temporal_capacity, bool) or not isinstance(self.temporal_capacity, int) or self.temporal_capacity <= 0:
            raise ValueError("temporal_capacity must be a positive integer")
        if (
            isinstance(self.base_cost, bool)
            or not isinstance(self.base_cost, (int, float))
            or not math.isfinite(float(self.base_cost))
            or self.base_cost <= 0.0
        ):
            raise ValueError("base_cost must be finite and positive")


DEFAULT_MODALITIES: tuple[SensoryModality, ...] = (
    SensoryModality(
        "modality.identity",
        (TransductionKind.IDENTITY,),
        max_inputs=1,
        temporal_capacity=1,
        base_cost=0.001,
    ),
    SensoryModality(
        "modality.alpha",
        (TransductionKind.IDENTITY, TransductionKind.DIFFERENCE, TransductionKind.THRESHOLD),
        max_inputs=1,
        temporal_capacity=2,
        base_cost=0.002,
    ),
    SensoryModality(
        "modality.beta",
        (TransductionKind.IDENTITY, TransductionKind.INTEGRATE),
        max_inputs=1,
        temporal_capacity=64,
        base_cost=0.003,
    ),
    SensoryModality(
        "modality.gamma",
        (TransductionKind.IDENTITY, TransductionKind.MIX, TransductionKind.DIFFERENCE, TransductionKind.INTEGRATE),
        max_inputs=4,
        temporal_capacity=8,
        base_cost=0.005,
    ),
)
