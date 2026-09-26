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
    """Bounded generated-use aggregates kept apart from factual observations."""

    MAX_REPRESENTATIONS = 256
    MAX_EPISODES_PER_REPRESENTATION = 64
    MAX_SOURCES_PER_REPRESENTATION = 64

    def __init__(self) -> None:
        self._activation_counts: dict[str, int] = {}
        self._episodes: dict[str, set[str]] = {}
        self._sources: dict[str, set[str]] = {}
        self._hypothesis_counts: dict[str, int] = {}
        self._disagreement_sum: dict[str, float] = {}
        self._disagreement_count: dict[str, int] = {}

    def record(
        self,
        *,
        representation_ref: str,
        episode_id: str,
        state_id: str,
        model_ids: tuple[str, ...] = (),
        source_refs: tuple[str, ...] = (),
        hypothesis_ref: str | None = None,
        model_disagreement: float = 0.0,
    ) -> None:
        bounded_identifier(representation_ref, name="representation_ref")
        bounded_identifier(episode_id, name="episode_id")
        bounded_identifier(state_id, name="state_id")
        if not isinstance(model_ids, tuple) or not isinstance(source_refs, tuple):
            raise ValueError("model_ids and source_refs must be tuples")
        for model_id in model_ids:
            bounded_identifier(model_id, name="model_id")
        for source_ref in source_refs:
            bounded_identifier(source_ref, name="source_ref")
        if hypothesis_ref is not None:
            bounded_identifier(hypothesis_ref, name="hypothesis_ref")
        unit_interval(model_disagreement, name="model_disagreement")

        if (
            representation_ref not in self._activation_counts
            and len(self._activation_counts) >= self.MAX_REPRESENTATIONS
        ):
            victim = next(iter(self._activation_counts))
            self._drop(victim)

        self._activation_counts[representation_ref] = min(
            1_000_000,
            self._activation_counts.get(representation_ref, 0) + 1,
        )
        episodes = self._episodes.setdefault(representation_ref, set())
        if len(episodes) < self.MAX_EPISODES_PER_REPRESENTATION:
            episodes.add(episode_id)
        sources = self._sources.setdefault(representation_ref, set())
        for source_ref in source_refs:
            if len(sources) >= self.MAX_SOURCES_PER_REPRESENTATION:
                break
            sources.add(source_ref)
        if hypothesis_ref is not None:
            self._hypothesis_counts[representation_ref] = min(
                1_000_000,
                self._hypothesis_counts.get(representation_ref, 0) + 1,
            )
        self._disagreement_sum[representation_ref] = min(
            1_000_000.0,
            self._disagreement_sum.get(representation_ref, 0.0) + model_disagreement,
        )
        self._disagreement_count[representation_ref] = min(
            1_000_000,
            self._disagreement_count.get(representation_ref, 0) + 1,
        )

    def note_factual_sources(
        self,
        *,
        representation_ref: str,
        source_refs: tuple[str, ...],
    ) -> None:
        """Attach independently observed provenance after reconciliation.

        This does not increment activation or factual observation counts.  It
        only records which factual sources have later supported/contradicted a
        representation that was already used generatively.
        """
        bounded_identifier(representation_ref, name="representation_ref")
        if not isinstance(source_refs, tuple):
            raise ValueError("source_refs must be a tuple")
        sources = self._sources.setdefault(representation_ref, set())
        for source_ref in source_refs:
            bounded_identifier(source_ref, name="source_ref")
            if len(sources) >= self.MAX_SOURCES_PER_REPRESENTATION:
                break
            sources.add(source_ref)

    def signal(
        self, *, representation_ref: str, generative_demand: float
    ) -> GenerativeConsolidationSignal:
        bounded_identifier(representation_ref, name="representation_ref")
        unit_interval(generative_demand, name="generative_demand")
        count = self._activation_counts.get(representation_ref, 0)
        episodes = self._episodes.get(representation_ref, set())
        disagreement_count = self._disagreement_count.get(representation_ref, 0)
        return GenerativeConsolidationSignal(
            recurrent_activation=count,
            cross_episode_reuse=max(0, len(episodes) - 1),
            hypothesis_persistence=self._hypothesis_counts.get(representation_ref, 0),
            model_disagreement=(
                self._disagreement_sum.get(representation_ref, 0.0) / disagreement_count
                if disagreement_count
                else 0.0
            ),
            generative_demand=generative_demand,
            independent_episode_count=len(episodes),
            source_diversity=len(self._sources.get(representation_ref, set())),
        )

    @property
    def representation_refs(self) -> tuple[str, ...]:
        """Bounded durable representation ids with generative-use history."""
        return tuple(sorted(self._activation_counts))

    def checkpoint(self) -> dict[str, object]:
        return {
            "representations": [
                {
                    "representation_ref": representation_ref,
                    "activation_count": self._activation_counts[representation_ref],
                    "episode_ids": sorted(self._episodes.get(representation_ref, set())),
                    "source_refs": sorted(self._sources.get(representation_ref, set())),
                    "hypothesis_count": self._hypothesis_counts.get(representation_ref, 0),
                    "disagreement_sum": self._disagreement_sum.get(representation_ref, 0.0),
                    "disagreement_count": self._disagreement_count.get(representation_ref, 0),
                }
                for representation_ref in sorted(self._activation_counts)
            ]
        }

    @classmethod
    def from_checkpoint(cls, payload: object) -> "GenerativeUseTracker":
        if not isinstance(payload, dict):
            raise ValueError("generative-use checkpoint must be an object")
        raw = payload.get("representations", [])
        if not isinstance(raw, list) or len(raw) > cls.MAX_REPRESENTATIONS:
            raise ValueError("invalid generative-use representation collection")
        tracker = cls()
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("invalid generative-use representation")
            representation_ref = bounded_identifier(
                item.get("representation_ref"), name="representation_ref"
            )
            activation_count = int(item.get("activation_count", 0))
            hypothesis_count = int(item.get("hypothesis_count", 0))
            disagreement_sum = float(item.get("disagreement_sum", 0.0))
            disagreement_count = int(item.get("disagreement_count", 0))
            episode_ids = tuple(item.get("episode_ids", ()))
            source_refs = tuple(item.get("source_refs", ()))
            if (
                activation_count < 0
                or hypothesis_count < 0
                or disagreement_sum < 0.0
                or disagreement_count < 0
                or len(episode_ids) > cls.MAX_EPISODES_PER_REPRESENTATION
                or len(source_refs) > cls.MAX_SOURCES_PER_REPRESENTATION
            ):
                raise ValueError("invalid generative-use aggregate")
            tracker._activation_counts[representation_ref] = activation_count
            tracker._episodes[representation_ref] = {
                bounded_identifier(value, name="episode_id") for value in episode_ids
            }
            tracker._sources[representation_ref] = {
                bounded_identifier(value, name="source_ref") for value in source_refs
            }
            tracker._hypothesis_counts[representation_ref] = hypothesis_count
            tracker._disagreement_sum[representation_ref] = disagreement_sum
            tracker._disagreement_count[representation_ref] = disagreement_count
        return tracker

    def _drop(self, representation_ref: str) -> None:
        self._activation_counts.pop(representation_ref, None)
        self._episodes.pop(representation_ref, None)
        self._sources.pop(representation_ref, None)
        self._hypothesis_counts.pop(representation_ref, None)
        self._disagreement_sum.pop(representation_ref, None)
        self._disagreement_count.pop(representation_ref, None)


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
