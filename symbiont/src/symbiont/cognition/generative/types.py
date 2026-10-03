"""Bounded, provenance-carrying values for Generative Cognition v1.

This module deliberately contains no model, runtime, or apparatus imports.  The
values here describe temporary cognition; they do not constitute factual
evidence or action authority.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

_IDENTIFIER: Final = re.compile(r"^[\x21-\x7e]+$")
_MAX_ID: Final = 128
_MAX_TOKEN: Final = 96
_MAX_COLLECTION: Final = 256


class EpistemicOrigin(str, Enum):
    OBSERVED = "observed"
    REMEMBERED = "remembered"
    INFERRED = "inferred"
    REPLAYED = "replayed"
    IMAGINED = "imagined"
    COUNTERFACTUAL = "counterfactual"
    ABSTRACT = "abstract"


class GenerativeOperation(str, Enum):
    PREDICT = "predict"
    BRANCH = "branch"
    REPLAY = "replay"
    COUNTERFACTUAL = "counterfactual"
    RECOMBINE = "recombine"
    ABSTRACT = "abstract"
    ANALOGIZE = "analogize"
    COMPOSE = "compose"
    DECOMPOSE = "decompose"


class GenerativeMode(str, Enum):
    ONLINE = "online"
    IDLE = "idle"
    OFFLINE = "offline"


class GenerativeTermination(str, Enum):
    COMPLETED = "completed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MODEL_UNAVAILABLE = "model_unavailable"
    UNCERTAIN = "uncertain"
    INTERRUPTED = "interrupted"
    INVALID = "invalid"


def bounded_identifier(value: str, *, name: str = "identifier", limit: int = _MAX_ID) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > limit
        or not _IDENTIFIER.fullmatch(value)
    ):
        raise ValueError(
            f"{name} must be non-empty printable non-whitespace ASCII of length <= {limit}"
        )
    return value


def bounded_tuple(
    values: tuple[str, ...], *, name: str, limit: int = _MAX_COLLECTION
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > limit:
        raise ValueError(f"{name} must be a tuple with at most {limit} entries")
    return tuple(
        bounded_identifier(value, name=f"{name} entry", limit=_MAX_TOKEN) for value in values
    )


def unit_interval(value: float, *, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be a finite number")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return float(value)


@dataclass(frozen=True, slots=True)
class GeneratedFeature:
    token: str
    value_class: int | float | str | None
    confidence: float
    source_model_id: str | None = None

    def __post_init__(self) -> None:
        bounded_identifier(self.token, name="feature token", limit=_MAX_TOKEN)
        if self.value_class is not None and not isinstance(self.value_class, (int, float, str)):
            raise ValueError("feature value_class must be a scalar or None")
        if isinstance(self.value_class, bool):
            raise ValueError("feature value_class must not be bool")
        unit_interval(self.confidence, name="feature confidence")
        if self.source_model_id is not None:
            bounded_identifier(self.source_model_id, name="source_model_id")


@dataclass(frozen=True, slots=True)
class GenerativeState:
    state_id: str
    episode_id: str
    origin: EpistemicOrigin
    parent_state_id: str | None
    depth: int
    features: tuple[GeneratedFeature, ...]
    active_concept_ids: tuple[str, ...]
    relation_refs: tuple[str, ...]
    source_episode_ids: tuple[str, ...]
    source_model_ids: tuple[str, ...]
    source_state_ids: tuple[str, ...]
    uncertainty: float
    coherence: float
    generative_tick: int

    def __post_init__(self) -> None:
        bounded_identifier(self.state_id, name="state_id")
        bounded_identifier(self.episode_id, name="episode_id")
        if not isinstance(self.origin, EpistemicOrigin):
            raise ValueError("origin must be an EpistemicOrigin")
        if self.parent_state_id is not None:
            bounded_identifier(self.parent_state_id, name="parent_state_id")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int) or self.depth < 0:
            raise ValueError("depth must be a non-negative integer")
        if not isinstance(self.features, tuple) or len(self.features) > _MAX_COLLECTION:
            raise ValueError("features exceed the bounded collection size")
        if not all(isinstance(feature, GeneratedFeature) for feature in self.features):
            raise ValueError("features must contain GeneratedFeature values")
        bounded_tuple(self.active_concept_ids, name="active_concept_ids")
        bounded_tuple(self.relation_refs, name="relation_refs")
        bounded_tuple(self.source_episode_ids, name="source_episode_ids")
        bounded_tuple(self.source_model_ids, name="source_model_ids")
        bounded_tuple(self.source_state_ids, name="source_state_ids")
        unit_interval(self.uncertainty, name="uncertainty")
        unit_interval(self.coherence, name="coherence")
        if (
            isinstance(self.generative_tick, bool)
            or not isinstance(self.generative_tick, int)
            or self.generative_tick < 0
        ):
            raise ValueError("generative_tick must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class GenerativeTransition:
    transition_id: str
    episode_id: str
    source_state_id: str
    target_state_id: str
    operation: GenerativeOperation
    model_ids: tuple[str, ...]
    uncertainty_before: float
    uncertainty_after: float
    predicted_outcomes: tuple[str, ...]
    generative_tick: int

    def __post_init__(self) -> None:
        for name, value in (
            ("transition_id", self.transition_id),
            ("episode_id", self.episode_id),
            ("source_state_id", self.source_state_id),
            ("target_state_id", self.target_state_id),
        ):
            bounded_identifier(value, name=name)
        if not isinstance(self.operation, GenerativeOperation):
            raise ValueError("operation must be a GenerativeOperation")
        bounded_tuple(self.model_ids, name="model_ids")
        bounded_tuple(self.predicted_outcomes, name="predicted_outcomes", limit=128)
        unit_interval(self.uncertainty_before, name="uncertainty_before")
        unit_interval(self.uncertainty_after, name="uncertainty_after")
        if (
            isinstance(self.generative_tick, bool)
            or not isinstance(self.generative_tick, int)
            or self.generative_tick < 0
        ):
            raise ValueError("generative_tick must be a non-negative integer")


@dataclass(slots=True)
class GenerativeEpisode:
    episode_id: str
    organism_id: str
    target_id: str | None
    root_state_id: str
    mode: GenerativeMode
    started_symbiont_tick: int
    started_generative_tick: int
    source_episode_ids: tuple[str, ...] = ()
    state_count: int = 0
    transition_count: int = 0
    branch_count: int = 0
    max_depth_reached: int = 0
    termination_reason: GenerativeTermination | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("episode_id", self.episode_id),
            ("organism_id", self.organism_id),
            ("root_state_id", self.root_state_id),
        ):
            bounded_identifier(value, name=name)
        if self.target_id is not None:
            bounded_identifier(self.target_id, name="target_id")
        if not isinstance(self.mode, GenerativeMode):
            raise ValueError("mode must be a GenerativeMode")
        bounded_tuple(self.source_episode_ids, name="source_episode_ids")
        for name, value in (
            ("started_symbiont_tick", self.started_symbiont_tick),
            ("started_generative_tick", self.started_generative_tick),
            ("state_count", self.state_count),
            ("transition_count", self.transition_count),
            ("branch_count", self.branch_count),
            ("max_depth_reached", self.max_depth_reached),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.termination_reason is not None and not isinstance(
            self.termination_reason, GenerativeTermination
        ):
            raise ValueError("termination_reason must be a GenerativeTermination or None")


__all__ = [
    "EpistemicOrigin",
    "GeneratedFeature",
    "GenerativeEpisode",
    "GenerativeMode",
    "GenerativeOperation",
    "GenerativeState",
    "GenerativeTermination",
    "GenerativeTransition",
]
