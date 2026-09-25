"""Generative-use accounting kept separate from factual representation counts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .types import bounded_identifier, bounded_tuple, unit_interval


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


@dataclass(frozen=True, slots=True)
class GenerativeCandidateProjection:
    """Producer-neutral request for the existing structural contention layer."""

    candidate_id: str
    family: str
    producer_id: str
    eligible_tick: int
    mutation_payloads: tuple[str, ...]

    def __post_init__(self) -> None:
        bounded_identifier(self.candidate_id, name="candidate_id")
        bounded_identifier(self.family, name="family")
        bounded_identifier(self.producer_id, name="producer_id")
        if (
            isinstance(self.eligible_tick, bool)
            or not isinstance(self.eligible_tick, int)
            or self.eligible_tick < 0
        ):
            raise ValueError("eligible_tick must be a non-negative integer")
        bounded_tuple(self.mutation_payloads, name="mutation_payloads")
        if not self.mutation_payloads:
            raise ValueError("mutation_payloads must not be empty")


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

    def __init__(
        self,
        *,
        tracker: GenerativeUseTracker | None = None,
        minimum_cross_episode_reuse: int = 1,
        minimum_source_diversity: int = 2,
        minimum_demand: float = 0.5,
    ) -> None:
        self.tracker = tracker or GenerativeUseTracker()
        if (
            isinstance(minimum_cross_episode_reuse, bool)
            or not isinstance(minimum_cross_episode_reuse, int)
            or minimum_cross_episode_reuse < 0
        ):
            raise ValueError("minimum_cross_episode_reuse must be a non-negative integer")
        if (
            isinstance(minimum_source_diversity, bool)
            or not isinstance(minimum_source_diversity, int)
            or minimum_source_diversity < 0
        ):
            raise ValueError("minimum_source_diversity must be a non-negative integer")
        unit_interval(minimum_demand, name="minimum_demand")
        self.minimum_cross_episode_reuse = minimum_cross_episode_reuse
        self.minimum_source_diversity = minimum_source_diversity
        self.minimum_demand = minimum_demand

    def signal(
        self, *, representation_ref: str, generative_demand: float
    ) -> GenerativeConsolidationSignal:
        return self.tracker.signal(
            representation_ref=representation_ref, generative_demand=generative_demand
        )

    def is_mature(self, signal: GenerativeConsolidationSignal) -> bool:
        return (
            signal.cross_episode_reuse >= self.minimum_cross_episode_reuse
            and signal.source_diversity >= self.minimum_source_diversity
            and signal.generative_demand >= self.minimum_demand
        )

    def project_candidate(
        self,
        *,
        signal: GenerativeConsolidationSignal,
        candidate_id: str,
        eligible_tick: int,
        mutation_payloads: tuple[str, ...],
    ) -> GenerativeCandidateProjection | None:
        """Create a contention request, never apply a graph mutation."""

        if not self.is_mature(signal):
            return None
        return GenerativeCandidateProjection(
            candidate_id=candidate_id,
            family="generative",
            producer_id="producer.generative",
            eligible_tick=eligible_tick,
            mutation_payloads=mutation_payloads,
        )

    def submit_candidate(
        self,
        projection: GenerativeCandidateProjection,
        *,
        register: Callable[..., bool],
        mutations: tuple[object, ...],
    ) -> bool:
        """Delegate admission to an external StructuralContention owner."""

        if not isinstance(mutations, tuple) or not mutations:
            raise ValueError("mutations must be a non-empty tuple")
        return bool(
            register(
                candidate_id=projection.candidate_id,
                family=projection.family,
                producer_id=projection.producer_id,
                eligible_tick=projection.eligible_tick,
                mutations=mutations,
            )
        )


__all__ = [
    "GenerativeCandidateProjection",
    "GenerativeConsolidationSignal",
    "GenerativeConsolidator",
    "GenerativeUseTracker",
]
