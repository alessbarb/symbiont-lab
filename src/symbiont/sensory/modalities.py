from __future__ import annotations

from dataclasses import dataclass

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
        if not self.modality_id or any(ch.isspace() for ch in self.modality_id):
            raise ValueError("modality_id must be a non-empty token")
        if not self.allowed_transductions:
            raise ValueError("a modality must allow at least one transduction")
        if self.max_inputs <= 0 or self.temporal_capacity <= 0 or self.base_cost <= 0.0:
            raise ValueError("invalid modality bounds")


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
