"""Generative-use accounting kept separate from factual representation counts."""

from __future__ import annotations

from dataclasses import dataclass

from .types import bounded_identifier, unit_interval


@dataclass(frozen=True, slots=True)
class GenerativeConsolidationSignal:
    recurrent_activation: int
    cross_episode_reuse: int
    hypothesis_persistence: int
    model_disagreement: float
    generative_demand: float
    independent_episode_count: int
    source_diversity: int

    def __post_init__(self) -> None:
        for name, value in (
            ("recurrent_activation", self.recurrent_activation),
            ("cross_episode_reuse", self.cross_episode_reuse),
            ("hypothesis_persistence", self.hypothesis_persistence),
            ("independent_episode_count", self.independent_episode_count),
            ("source_diversity", self.source_diversity),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        unit_interval(self.model_disagreement, name="model_disagreement")
        unit_interval(self.generative_demand, name="generative_demand")


class GenerativeUseTracker:
    """Tracks generated use without touching factual observation counters."""

    def __init__(self) -> None:
        self._activations: dict[str, list[tuple[str, str]]] = {}
        self._models: dict[str, set[str]] = {}
        self._hypothesis_counts: dict[str, int] = {}
        self._disagreement: dict[str, list[float]] = {}

    def record(
        self,
        *,
        representation_ref: str,
        episode_id: str,
        state_id: str,
        model_ids: tuple[str, ...] = (),
        hypothesis_ref: str | None = None,
        model_disagreement: float = 0.0,
    ) -> None:
        bounded_identifier(representation_ref, name="representation_ref")
        bounded_identifier(episode_id, name="episode_id")
        bounded_identifier(state_id, name="state_id")
        if not isinstance(model_ids, tuple):
            raise ValueError("model_ids must be a tuple")
        for model_id in model_ids:
            bounded_identifier(model_id, name="model_id")
        if hypothesis_ref is not None:
            bounded_identifier(hypothesis_ref, name="hypothesis_ref")
        unit_interval(model_disagreement, name="model_disagreement")
        self._activations.setdefault(representation_ref, []).append((episode_id, state_id))
        self._models.setdefault(representation_ref, set()).update(model_ids)
        if hypothesis_ref is not None:
            self._hypothesis_counts[representation_ref] = (
                self._hypothesis_counts.get(representation_ref, 0) + 1
            )
        self._disagreement.setdefault(representation_ref, []).append(model_disagreement)

    def signal(
        self, *, representation_ref: str, generative_demand: float
    ) -> GenerativeConsolidationSignal:
        bounded_identifier(representation_ref, name="representation_ref")
        unit_interval(generative_demand, name="generative_demand")
        activations = self._activations.get(representation_ref, [])
        episodes = {episode_id for episode_id, _ in activations}
        disagreements = self._disagreement.get(representation_ref, [])
        return GenerativeConsolidationSignal(
            recurrent_activation=len(activations),
            cross_episode_reuse=max(0, len(episodes) - 1),
            hypothesis_persistence=self._hypothesis_counts.get(representation_ref, 0),
            model_disagreement=(sum(disagreements) / len(disagreements) if disagreements else 0.0),
            generative_demand=generative_demand,
            independent_episode_count=len(episodes),
            source_diversity=len(self._models.get(representation_ref, set())),
        )


class GenerativeConsolidator:
    """Produces signals only; structural admission remains another component's job."""

    def __init__(self, *, tracker: GenerativeUseTracker | None = None) -> None:
        self.tracker = tracker or GenerativeUseTracker()

    def signal(
        self, *, representation_ref: str, generative_demand: float
    ) -> GenerativeConsolidationSignal:
        return self.tracker.signal(
            representation_ref=representation_ref, generative_demand=generative_demand
        )


__all__ = ["GenerativeConsolidationSignal", "GenerativeConsolidator", "GenerativeUseTracker"]
