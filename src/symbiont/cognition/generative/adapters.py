"""Thin adapters over existing predictive owners.

Adapters only translate an existing query result into ``GeneratedProposal``.
They do not copy model state, train models, record evidence, or execute actions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .model import GeneratedProposal, GenerativeContext
from .types import GeneratedFeature, GenerativeOperation, GenerativeState, bounded_identifier


def _supports(operation: GenerativeOperation, state: GenerativeState) -> bool:
    return operation is GenerativeOperation.PREDICT and isinstance(state, GenerativeState)


@dataclass(frozen=True, slots=True)
class PrivateSLMGenerativeAdapter:
    """Adapts the existing competence counterfactual callback.

    The first context token is the opaque competence identifier; remaining
    tokens are passed unchanged to the private model owner.
    """

    model_id: str
    predictor: Callable[[str, tuple[str, ...]], Any]

    def __post_init__(self) -> None:
        bounded_identifier(self.model_id, name="model_id")

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return _supports(operation, state)

    def generate(
        self, *, state: GenerativeState, operation: GenerativeOperation, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]:
        if not self.supports(operation, state) or not context.tokens:
            return ()
        competence_id, model_context = context.tokens[0], context.tokens[1:]
        result = self.predictor(competence_id, model_context)
        predicted = _required_string(result, "predicted_token")
        confidence_class = _bounded_class(result, "confidence_class")
        return (_proposal(self.model_id, predicted, confidence_class, context.references),)


@dataclass(frozen=True, slots=True)
class SensorimotorDynamicsGenerativeAdapter:
    """Adapts a sensorimotor model query without taking model ownership."""

    model_id: str
    predictor: Callable[[GenerativeContext], Mapping[str, float]]

    def __post_init__(self) -> None:
        bounded_identifier(self.model_id, name="model_id")

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return _supports(operation, state)

    def generate(
        self, *, state: GenerativeState, operation: GenerativeOperation, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]:
        if not self.supports(operation, state):
            return ()
        values = self.predictor(context)
        if not isinstance(values, Mapping):
            raise ValueError("sensorimotor adapter predictor must return a mapping")
        features = tuple(
            GeneratedFeature(str(key), float(value), 0.5, self.model_id)
            for key, value in sorted(values.items(), key=lambda item: str(item[0]))
        )
        return (
            GeneratedProposal(
                features,
                tuple(str(key) for key in sorted(values, key=str)),
                0.5,
                1.0,
                self.model_id,
                context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class CompetenceEffectGenerativeAdapter:
    """Adapts a competence/effect prediction callback."""

    model_id: str
    predictor: Callable[[str, str | None], Any]

    def __post_init__(self) -> None:
        bounded_identifier(self.model_id, name="model_id")

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return _supports(operation, state)

    def generate(
        self, *, state: GenerativeState, operation: GenerativeOperation, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]:
        if not self.supports(operation, state) or not context.tokens:
            return ()
        competence_id = context.tokens[0]
        context_id = context.tokens[1] if len(context.tokens) > 1 else None
        result = self.predictor(competence_id, context_id)
        if result is None:
            return ()
        effect = _required_string(result, "effect_id")
        confidence = _bounded_float(result, "confidence")
        feature = GeneratedFeature(effect, None, confidence, self.model_id)
        return (
            GeneratedProposal(
                (feature,),
                (effect,),
                1.0 - confidence,
                confidence,
                self.model_id,
                context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class EpisodicReplayAdapter:
    """Adapts a bounded episodic projection into replayed generated features."""

    model_id: str
    projector: Callable[[GenerativeContext], tuple[GeneratedFeature, ...]]

    def __post_init__(self) -> None:
        bounded_identifier(self.model_id, name="model_id")

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.REPLAY and isinstance(state, GenerativeState)

    def generate(
        self, *, state: GenerativeState, operation: GenerativeOperation, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]:
        if not self.supports(operation, state):
            return ()
        features = self.projector(context)
        if not isinstance(features, tuple) or not all(
            isinstance(item, GeneratedFeature) for item in features
        ):
            raise ValueError("episodic projector must return tuple[GeneratedFeature, ...]")
        return (
            GeneratedProposal(
                features,
                tuple(item.token for item in features),
                0.75,
                0.75,
                self.model_id,
                context.references,
            ),
        )


def _required_string(result: Any, name: str) -> str:
    value = getattr(result, name, None)
    if not isinstance(value, str) or not value:
        raise ValueError(f"adapter result requires non-empty {name}")
    return value


def _bounded_class(result: Any, name: str) -> int:
    value = getattr(result, name, None)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 7:
        raise ValueError(f"adapter result {name} must be an integer in [0, 7]")
    return value


def _bounded_float(result: Any, name: str) -> float:
    value = getattr(result, name, None)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"adapter result {name} must be within [0, 1]")
    return float(value)


def _proposal(
    model_id: str, predicted: str, confidence_class: int, refs: tuple[str, ...]
) -> GeneratedProposal:
    confidence = confidence_class / 7.0 if confidence_class else 0.0
    return GeneratedProposal(
        (GeneratedFeature(predicted, None, confidence, model_id),),
        (predicted,),
        1.0 - confidence,
        confidence,
        model_id,
        refs,
    )


__all__ = [
    "CompetenceEffectGenerativeAdapter",
    "EpisodicReplayAdapter",
    "PrivateSLMGenerativeAdapter",
    "SensorimotorDynamicsGenerativeAdapter",
]
