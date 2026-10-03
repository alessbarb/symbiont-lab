"""Materialize bounded episodic projections as replayed cognition."""

from __future__ import annotations

from dataclasses import dataclass

from .types import (
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeState,
    bounded_identifier,
    unit_interval,
)
from .workspace import GenerativeWorkspace


@dataclass(frozen=True, slots=True)
class ReplayFragment:
    """An organism-owned projection of one factual episode, not new evidence."""

    source_episode_id: str
    source_state_id: str
    features: tuple[GeneratedFeature, ...]
    uncertainty: float
    coherence: float

    def __post_init__(self) -> None:
        bounded_identifier(self.source_episode_id, name="source_episode_id")
        bounded_identifier(self.source_state_id, name="source_state_id")
        if not isinstance(self.features, tuple) or not all(
            isinstance(item, GeneratedFeature) for item in self.features
        ):
            raise ValueError("features must be a tuple of GeneratedFeature values")
        unit_interval(self.uncertainty, name="uncertainty")
        unit_interval(self.coherence, name="coherence")


class ReplayEngine:
    """Copies a bounded projection without recording a factual observation."""

    def __init__(self, *, workspace: GenerativeWorkspace) -> None:
        self.workspace = workspace

    def materialize(self, fragment: ReplayFragment) -> GenerativeState:
        if self.workspace.states:
            raise ValueError("replay materialization requires an empty workspace")
        state = GenerativeState(
            state_id=self.workspace.episode.root_state_id,
            episode_id=self.workspace.episode.episode_id,
            origin=EpistemicOrigin.REPLAYED,
            parent_state_id=None,
            depth=0,
            features=fragment.features,
            active_concept_ids=(),
            relation_refs=(),
            source_episode_ids=(fragment.source_episode_id,),
            source_model_ids=(),
            source_state_ids=(fragment.source_state_id,),
            uncertainty=fragment.uncertainty,
            coherence=fragment.coherence,
            generative_tick=self.workspace.episode.started_generative_tick,
        )
        self.workspace.add_state(state)
        return state


__all__ = ["ReplayEngine", "ReplayFragment"]
