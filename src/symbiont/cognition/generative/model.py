"""Common model boundary for generative queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .types import (
    GeneratedFeature,
    GenerativeOperation,
    GenerativeState,
    bounded_identifier,
    bounded_tuple,
    unit_interval,
)


@dataclass(frozen=True, slots=True)
class GenerativeContext:
    """Opaque, caller-owned query context; it carries no evaluator semantics."""

    tokens: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        bounded_tuple(self.tokens, name="context tokens")
        bounded_tuple(self.references, name="context references")


@dataclass(frozen=True, slots=True)
class GeneratedProposal:
    features: tuple[GeneratedFeature, ...]
    predicted_outcomes: tuple[str, ...]
    uncertainty: float
    coherence: float
    model_id: str
    support_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.features, tuple) or not all(
            isinstance(item, GeneratedFeature) for item in self.features
        ):
            raise ValueError("features must be a tuple of GeneratedFeature values")
        bounded_tuple(self.predicted_outcomes, name="predicted_outcomes", limit=128)
        unit_interval(self.uncertainty, name="uncertainty")
        unit_interval(self.coherence, name="coherence")
        bounded_identifier(self.model_id, name="model_id")
        bounded_tuple(self.support_refs, name="support_refs")


@runtime_checkable
class GenerativeModel(Protocol):
    @property
    def model_id(self) -> str: ...

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool: ...

    def generate(
        self, *, state: GenerativeState, operation: GenerativeOperation, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]: ...


__all__ = ["GeneratedProposal", "GenerativeContext", "GenerativeModel"]
