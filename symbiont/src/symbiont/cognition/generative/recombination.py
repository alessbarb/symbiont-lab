"""Compatibility-gated recombination of organism-owned episode fragments."""

from __future__ import annotations

from dataclasses import dataclass

from .types import (
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeState,
    bounded_identifier,
    bounded_tuple,
    unit_interval,
)
from .workspace import BudgetExceeded, GenerativeWorkspace


@dataclass(frozen=True, slots=True)
class RecombinationFragment:
    source_episode_id: str
    source_state_id: str
    features: tuple[GeneratedFeature, ...]
    compatibility_keys: tuple[str, ...]
    uncertainty: float
    coherence: float

    def __post_init__(self) -> None:
        bounded_identifier(self.source_episode_id, name="source_episode_id")
        bounded_identifier(self.source_state_id, name="source_state_id")
        if not isinstance(self.features, tuple) or not all(
            isinstance(item, GeneratedFeature) for item in self.features
        ):
            raise ValueError("features must be a tuple of GeneratedFeature values")
        bounded_tuple(self.compatibility_keys, name="compatibility_keys")
        unit_interval(self.uncertainty, name="uncertainty")
        unit_interval(self.coherence, name="coherence")


class ExperienceRecombiner:
    """Creates novel generated states only from compatible fragments."""

    def __init__(self, *, workspace: GenerativeWorkspace) -> None:
        self.workspace = workspace

    def combine(self, left: RecombinationFragment, right: RecombinationFragment) -> GenerativeState:
        shared_keys = tuple(sorted(set(left.compatibility_keys) & set(right.compatibility_keys)))
        if not shared_keys:
            raise ValueError(
                "recombination fragments have no organism-owned compatibility relation"
            )
        features = left.features + right.features
        state_id = (
            self.workspace.episode.root_state_id
            if not self.workspace.states
            else f"{self.workspace.episode.episode_id}.s{len(self.workspace.states)}"
        )
        state = GenerativeState(
            state_id=state_id,
            episode_id=self.workspace.episode.episode_id,
            origin=EpistemicOrigin.IMAGINED,
            parent_state_id=None,
            depth=0,
            features=features,
            active_concept_ids=shared_keys,
            relation_refs=shared_keys,
            source_episode_ids=_unique_pair(left.source_episode_id, right.source_episode_id),
            source_model_ids=(),
            source_state_ids=_unique_pair(left.source_state_id, right.source_state_id),
            uncertainty=max(left.uncertainty, right.uncertainty),
            coherence=min(left.coherence, right.coherence),
            generative_tick=self.workspace.episode.started_generative_tick,
        )
        try:
            self.workspace.add_state(state)
        except BudgetExceeded:
            raise
        return state


def _unique_pair(left: str, right: str) -> tuple[str, ...]:
    return (left,) if left == right else (left, right)


__all__ = ["ExperienceRecombiner", "RecombinationFragment"]
