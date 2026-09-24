from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence

from ..cognition.limits import KernelLimits
from .experience import EpistemicStatus, ExperienceRecord, SourceKind


class EpisodicMemoryError(ValueError):
    """Raised when episodic state is invalid or exceeds kernel limits."""


def _valid_token(value: object, *, max_length: int = 128) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= max_length
        and all(0x20 < ord(char) < 0x7F for char in value)
    )


def _bounded_unique(values: Iterable[str], *, limit: int) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw)
        if not _valid_token(value) or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return tuple(result)


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a = set(left)
    b = set(right)
    if not a and not b:
        return 1.0
    union = a | b
    return 0.0 if not union else len(a & b) / len(union)


def _is_causal_observation(record: ExperienceRecord) -> bool:
    return (
        record.record_id.startswith("transition.")
        and record.epistemic_status is EpistemicStatus.OBSERVED
        and record.source_kind is not SourceKind.MODEL
    )


def _coarse_effect_features(outcomes: Sequence[str]) -> tuple[str, ...]:
    """Project raw outcome vocabulary into a compact, semantics-free effect shape."""
    directions: Counter[str] = Counter()
    magnitudes: list[int] = []
    channel_directions: list[str] = []
    internal: list[str] = []

    for token in outcomes:
        parts = token.split(".")
        if token.startswith("outcome.sense.") and len(parts) >= 4:
            direction_index = None
            for index in range(len(parts) - 1, 1, -1):
                if parts[index] in {"up", "down"}:
                    direction_index = index
                    break
            if direction_index is not None:
                direction = parts[direction_index]
                directions[direction] += 1
                channel = ".".join(parts[:direction_index])
                channel_directions.append(f"{channel}.{direction}")
                if direction_index + 1 < len(parts):
                    try:
                        magnitudes.append(int(parts[direction_index + 1]))
                    except ValueError:
                        pass
                continue
        if token.startswith("outcome."):
            internal.append(token)

    total_changed = directions["up"] + directions["down"]
    features: list[str] = []
    if total_changed:
        balance = directions["up"] - directions["down"]
        if abs(balance) <= max(1, total_changed // 5):
            features.append("effect.balance.mixed")
        elif balance > 0:
            features.append("effect.balance.up")
        else:
            features.append("effect.balance.down")

        spread_ratio = min(1.0, total_changed / 16.0)
        spread = "low" if spread_ratio < 0.34 else "medium" if spread_ratio < 0.67 else "high"
        features.append(f"effect.spread.{spread}")

    if magnitudes:
        mean_magnitude = sum(magnitudes) / len(magnitudes)
        intensity = "low" if mean_magnitude < 2.5 else "medium" if mean_magnitude < 5.0 else "high"
        features.append(f"effect.intensity.{intensity}")

    # Preserve a small amount of channel-specific causal structure without
    # carrying hundreds of raw outcome tokens into long-horizon memory.
    features.extend(sorted(set(channel_directions))[:8])
    features.extend(sorted(set(internal))[:4])
    if not features:
        features.append("effect.stable")
    return _bounded_unique(features, limit=16)


@dataclass(frozen=True, slots=True)
class EpisodicProjection:
    """Sparse organism-native representation used for episodic similarity.

    IDs are direct identities already present in the organism's cognitive
    apparatus. No laboratory/world labels are admitted.
    """

    sense_ids: tuple[str, ...] = ()
    concept_ids: tuple[str, ...] = ()
    internal_tokens: tuple[str, ...] = ()
    action_token: str | None = None
    effect_features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, values, maximum in (
            ("sense_ids", self.sense_ids, 16),
            ("concept_ids", self.concept_ids, 8),
            ("internal_tokens", self.internal_tokens, 8),
            ("effect_features", self.effect_features, 16),
        ):
            if not isinstance(values, tuple) or len(values) > maximum:
                raise EpisodicMemoryError(f"{name} exceeds episodic projection bound")
            if any(not _valid_token(value) for value in values):
                raise EpisodicMemoryError(f"{name} contains invalid token")
        if self.action_token is not None and not _valid_token(self.action_token):
            raise EpisodicMemoryError("invalid episodic action token")

    @property
    def context_tokens(self) -> tuple[str, ...]:
        return (
            *self.sense_ids,
            *self.concept_ids,
            *self.internal_tokens,
        )

    def with_effects(self, outcomes: Sequence[str]) -> "EpisodicProjection":
        return EpisodicProjection(
            sense_ids=self.sense_ids,
            concept_ids=self.concept_ids,
            internal_tokens=self.internal_tokens,
            action_token=self.action_token,
            effect_features=_coarse_effect_features(outcomes),
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "sense_ids": list(self.sense_ids),
            "concept_ids": list(self.concept_ids),
            "internal_tokens": list(self.internal_tokens),
            "action_token": self.action_token,
            "effect_features": list(self.effect_features),
        }

    @classmethod
    def from_record(cls, record: ExperienceRecord) -> "EpisodicProjection":
        senses = [
            token.removeprefix("sense.")
            for token in record.context_tokens
            if token.startswith("sense.")
        ]
        concepts = [
            token.removeprefix("concept.")
            for token in record.context_tokens
            if token.startswith("concept.")
        ]
        internal = [
            token
            for token in record.context_tokens
            if token.startswith("internal.")
        ]
        return cls(
            sense_ids=_bounded_unique(senses, limit=16),
            concept_ids=_bounded_unique(concepts, limit=8),
            internal_tokens=_bounded_unique(internal, limit=8),
            action_token=record.action_token,
            effect_features=_coarse_effect_features(record.outcome_tokens),
        )

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "EpisodicProjection":
        def values(name: str, maximum: int) -> tuple[str, ...]:
            raw = payload.get(name, [])
            if not isinstance(raw, list) or len(raw) > maximum:
                raise EpisodicMemoryError(f"invalid episodic projection {name}")
            result = tuple(raw)
            if any(not _valid_token(item) for item in result):
                raise EpisodicMemoryError(f"invalid episodic projection {name}")
            return result

        action = payload.get("action_token")
        if action is not None and not _valid_token(action):
            raise EpisodicMemoryError("invalid episodic projection action")
        return cls(
            sense_ids=values("sense_ids", 16),
            concept_ids=values("concept_ids", 8),
            internal_tokens=values("internal_tokens", 8),
            action_token=action,
            effect_features=values("effect_features", 16),
        )


@dataclass(frozen=True, slots=True)
class EpisodeStep:
    """Compact immutable provenance for one causal record inside an episode."""

    tick_offset: int
    source_record_id: str
    source_content_hash: str
    evidence_refs: tuple[str, ...]
    source_kind: SourceKind

    def __post_init__(self) -> None:
        if isinstance(self.tick_offset, bool) or not isinstance(self.tick_offset, int) or self.tick_offset < 0:
            raise EpisodicMemoryError("tick_offset must be non-negative")
        if not _valid_token(self.source_record_id):
            raise EpisodicMemoryError("invalid episodic source record id")
        if (
            not isinstance(self.source_content_hash, str)
            or len(self.source_content_hash) != 64
            or any(char not in "0123456789abcdef" for char in self.source_content_hash)
        ):
            raise EpisodicMemoryError("invalid episodic source content hash")
        if len(self.evidence_refs) > 8 or any(not _valid_token(ref) for ref in self.evidence_refs):
            raise EpisodicMemoryError("invalid episodic evidence refs")
        if not isinstance(self.source_kind, SourceKind) or self.source_kind is SourceKind.MODEL:
            raise EpisodicMemoryError("invalid episodic source kind")

    def checkpoint(self) -> dict[str, object]:
        return {
            "tick_offset": self.tick_offset,
            "source_record_id": self.source_record_id,
            "source_content_hash": self.source_content_hash,
            "evidence_refs": list(self.evidence_refs),
            "source_kind": self.source_kind.value,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "EpisodeStep":
        try:
            raw_refs = payload["evidence_refs"]
            if not isinstance(raw_refs, list):
                raise EpisodicMemoryError("invalid episodic step evidence")
            return cls(
                tick_offset=int(payload["tick_offset"]),
                source_record_id=str(payload["source_record_id"]),
                source_content_hash=str(payload["source_content_hash"]),
                evidence_refs=tuple(str(item) for item in raw_refs),
                source_kind=SourceKind(str(payload["source_kind"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, EpisodicMemoryError):
                raise
            raise EpisodicMemoryError("invalid episodic step checkpoint") from exc


@dataclass(slots=True)
class ExperienceEpisode:
    """A recurring episodic family with compact prototypes and provenance."""

    episode_id: str
    start_tick: int
    end_tick: int
    occurrence_ticks: tuple[int, ...]
    trace: tuple[EpisodeStep, ...]
    action_token: str | None
    sense_support: dict[str, int]
    concept_support: dict[str, int]
    internal_support: dict[str, int]
    effect_support: dict[str, int]
    exceptions: tuple[EpisodicProjection, ...]
    evidence_refs: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    novelty: float
    surprise: float
    recurrence: int = 1
    compressed: bool = False

    def __post_init__(self) -> None:
        if not _valid_token(self.episode_id):
            raise EpisodicMemoryError("invalid episode id")
        if self.start_tick < 0 or self.end_tick < self.start_tick:
            raise EpisodicMemoryError("invalid episode tick range")
        if not self.occurrence_ticks or tuple(sorted(set(self.occurrence_ticks))) != self.occurrence_ticks:
            raise EpisodicMemoryError("invalid episode occurrence ticks")
        if self.recurrence < len(self.occurrence_ticks) or self.recurrence < 1:
            raise EpisodicMemoryError("invalid episode recurrence")
        if len(self.trace) > 8 or any(not isinstance(step, EpisodeStep) for step in self.trace):
            raise EpisodicMemoryError("invalid episodic provenance trace")
        for name, support, maximum in (
            ("sense_support", self.sense_support, 32),
            ("concept_support", self.concept_support, 16),
            ("internal_support", self.internal_support, 16),
            ("effect_support", self.effect_support, 32),
        ):
            if len(support) > maximum:
                raise EpisodicMemoryError(f"{name} exceeds family feature bound")
            if any(
                not _valid_token(key)
                or isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                or value > self.recurrence
                for key, value in support.items()
            ):
                raise EpisodicMemoryError(f"invalid {name}")
        if self.action_token is not None and not _valid_token(self.action_token):
            raise EpisodicMemoryError("invalid episode action")
        if (
            not isinstance(self.exceptions, tuple)
            or len(self.exceptions) > 4
            or any(not isinstance(item, EpisodicProjection) for item in self.exceptions)
        ):
            raise EpisodicMemoryError("invalid episodic exceptions")
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in (self.novelty, self.surprise)):
            raise EpisodicMemoryError("invalid episodic novelty/surprise")

    @staticmethod
    def _prototype(support: Mapping[str, int], recurrence: int, *, limit: int) -> tuple[str, ...]:
        if not support:
            return ()
        threshold = max(1, math.ceil(recurrence * 0.40))
        ranked = sorted(
            support.items(),
            key=lambda item: (-item[1], item[0]),
        )
        selected = [token for token, count in ranked if count >= threshold]
        if not selected:
            selected = [token for token, _ in ranked[: min(limit, 4)]]
        return tuple(selected[:limit])

    @property
    def projection(self) -> EpisodicProjection:
        return EpisodicProjection(
            sense_ids=self._prototype(self.sense_support, self.recurrence, limit=16),
            concept_ids=self._prototype(self.concept_support, self.recurrence, limit=8),
            internal_tokens=self._prototype(self.internal_support, self.recurrence, limit=8),
            action_token=self.action_token,
            effect_features=self._prototype(self.effect_support, self.recurrence, limit=16),
        )

    # Compatibility surfaces retained for existing passive tooling.
    @property
    def initial_context(self) -> tuple[str, ...]:
        return self.projection.context_tokens

    @property
    def terminal_context(self) -> tuple[str, ...]:
        return (*self.projection.context_tokens, *self.projection.effect_features)

    @property
    def action_tokens(self) -> tuple[str, ...]:
        return () if self.action_token is None else (self.action_token,)

    @property
    def outcome_tokens(self) -> tuple[str, ...]:
        return self.projection.effect_features

    def checkpoint(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "occurrence_ticks": list(self.occurrence_ticks),
            "trace": [step.checkpoint() for step in self.trace],
            "action_token": self.action_token,
            "sense_support": dict(sorted(self.sense_support.items())),
            "concept_support": dict(sorted(self.concept_support.items())),
            "internal_support": dict(sorted(self.internal_support.items())),
            "effect_support": dict(sorted(self.effect_support.items())),
            "exceptions": [item.checkpoint() for item in self.exceptions],
            "evidence_refs": list(self.evidence_refs),
            "source_record_ids": list(self.source_record_ids),
            "novelty": self.novelty,
            "surprise": self.surprise,
            "recurrence": self.recurrence,
            "compressed": self.compressed,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "ExperienceEpisode":
        def support(name: str, maximum: int, recurrence: int) -> dict[str, int]:
            raw = payload.get(name, {})
            if not isinstance(raw, Mapping) or len(raw) > maximum:
                raise EpisodicMemoryError(f"invalid {name}")
            result: dict[str, int] = {}
            for key, value in raw.items():
                if (
                    not _valid_token(key)
                    or isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                    or value > recurrence
                ):
                    raise EpisodicMemoryError(f"invalid {name}")
                result[str(key)] = value
            return result

        try:
            recurrence = int(payload.get("recurrence", 1))
            raw_occurrences = payload["occurrence_ticks"]
            raw_trace = payload.get("trace", [])
            if not isinstance(raw_occurrences, list) or not isinstance(raw_trace, list):
                raise EpisodicMemoryError("invalid episode collections")
            raw_evidence = payload.get("evidence_refs", [])
            raw_sources = payload.get("source_record_ids", [])
            raw_exceptions = payload.get("exceptions", [])
            if (
                not isinstance(raw_evidence, list)
                or not isinstance(raw_sources, list)
                or not isinstance(raw_exceptions, list)
                or len(raw_exceptions) > 4
                or any(not isinstance(item, Mapping) for item in raw_exceptions)
            ):
                raise EpisodicMemoryError("invalid episode provenance")
            return cls(
                episode_id=str(payload["episode_id"]),
                start_tick=int(payload["start_tick"]),
                end_tick=int(payload["end_tick"]),
                occurrence_ticks=tuple(int(tick) for tick in raw_occurrences),
                trace=tuple(EpisodeStep.restore(step) for step in raw_trace if isinstance(step, Mapping)),
                action_token=payload.get("action_token") if isinstance(payload.get("action_token"), str) else None,
                sense_support=support("sense_support", 32, recurrence),
                concept_support=support("concept_support", 16, recurrence),
                internal_support=support("internal_support", 16, recurrence),
                effect_support=support("effect_support", 32, recurrence),
                exceptions=tuple(
                    EpisodicProjection.restore(item)
                    for item in raw_exceptions
                ),
                evidence_refs=_bounded_unique((str(item) for item in raw_evidence), limit=32),
                source_record_ids=_bounded_unique((str(item) for item in raw_sources), limit=32),
                novelty=float(payload["novelty"]),
                surprise=float(payload["surprise"]),
                recurrence=recurrence,
                compressed=bool(payload.get("compressed", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, EpisodicMemoryError):
                raise
            raise EpisodicMemoryError("invalid episode checkpoint") from exc


@dataclass(frozen=True, slots=True)
class EpisodeMatch:
    episode_id: str
    similarity: float
    episode: ExperienceEpisode
    interpretations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsolidatedContingency:
    contingency_id: str
    context_tokens: tuple[str, ...]
    sense_ids: tuple[str, ...]
    concept_ids: tuple[str, ...]
    action_token: str | None
    outcome_tokens: tuple[str, ...]
    support_episode_ids: tuple[str, ...]
    support_epochs: int
    confidence: float


@dataclass(frozen=True, slots=True)
class EpisodicPrediction:
    action_token: str | None
    predicted_outcomes: tuple[str, ...]
    confidence: float
    support_episode_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CognitiveReplay:
    episode_id: str
    similarity: float
    trace: tuple[EpisodeStep, ...]
    context_tokens: tuple[str, ...]
    action_tokens: tuple[str, ...]
    outcome_tokens: tuple[str, ...]
    interpretations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EpisodicMemoryMetrics:
    episode_count: int
    pending_records: int
    compressed_episode_count: int
    interpretation_count: int
    consolidated_contingencies: int
    retrieval_count: int
    replay_count: int
    compaction_count: int
    eviction_count: int
    oldest_episode_age: int
    mean_episode_age: float


@dataclass(slots=True)
class _PendingObservation:
    record: ExperienceRecord
    projection: EpisodicProjection


class EpisodicExperienceMemory:
    """Sparse, bounded, cognitively indexed long-horizon episodic memory."""

    SCHEMA_VERSION = 2
    _STATE_FAMILY_THRESHOLD = 0.48
    _EFFECT_FAMILY_THRESHOLD = 0.42

    def __init__(
        self,
        organism_id: str,
        *,
        kernel_limits: KernelLimits | None = None,
    ) -> None:
        if not _valid_token(organism_id):
            raise EpisodicMemoryError("invalid episodic organism id")
        self._organism_id = organism_id
        self._limits = kernel_limits or KernelLimits()
        self._episodes: list[ExperienceEpisode] = []
        self._pending: list[_PendingObservation] = []
        self._interpretations: dict[str, set[str]] = {}
        self._retrieval_counts: Counter[str] = Counter()
        self._consolidated: dict[str, ConsolidatedContingency] = {}
        self._retrieval_count = 0
        self._replay_count = 0
        self._compaction_count = 0
        self._eviction_count = 0

    @property
    def organism_id(self) -> str:
        return self._organism_id

    @property
    def episodes(self) -> tuple[ExperienceEpisode, ...]:
        return tuple(self._episodes)

    @property
    def consolidated(self) -> tuple[ConsolidatedContingency, ...]:
        return tuple(self._consolidated[key] for key in sorted(self._consolidated))

    def interpretations_for(self, episode_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._interpretations.get(episode_id, ())))

    @staticmethod
    def projection_similarity(
        left: EpisodicProjection,
        right: EpisodicProjection,
        *,
        include_effect: bool = False,
    ) -> float:
        components: list[tuple[float, float]] = []
        if left.sense_ids or right.sense_ids:
            components.append((0.42, _jaccard(left.sense_ids, right.sense_ids)))
        if left.concept_ids or right.concept_ids:
            components.append((0.28, _jaccard(left.concept_ids, right.concept_ids)))
        if left.internal_tokens or right.internal_tokens:
            components.append((0.15, _jaccard(left.internal_tokens, right.internal_tokens)))
        components.append(
            (0.15, 1.0 if left.action_token == right.action_token else 0.0)
        )
        total_weight = sum(weight for weight, _ in components)
        state = sum(weight * value for weight, value in components) / total_weight
        if not include_effect:
            return state
        effect = _jaccard(left.effect_features, right.effect_features)
        return 0.62 * state + 0.38 * effect

    @staticmethod
    def _effect_similarity(left: EpisodicProjection, right: EpisodicProjection) -> float:
        left_summary = tuple(
            token for token in left.effect_features if token.startswith("effect.")
        )
        right_summary = tuple(
            token for token in right.effect_features if token.startswith("effect.")
        )
        left_channels = tuple(
            token for token in left.effect_features if not token.startswith("effect.")
        )
        right_channels = tuple(
            token for token in right.effect_features if not token.startswith("effect.")
        )
        summary = _jaccard(left_summary, right_summary)
        channels = _jaccard(left_channels, right_channels)
        if not left_channels and not right_channels:
            return summary
        return 0.72 * summary + 0.28 * channels

    def _family_match(
        self,
        episode: ExperienceEpisode,
        projection: EpisodicProjection,
    ) -> tuple[float, float]:
        candidates = (episode.projection, *episode.exceptions)
        best_state = 0.0
        best_effect = 0.0
        best_joint = -1.0
        for candidate in candidates:
            state = self.projection_similarity(candidate, projection)
            effect = self._effect_similarity(candidate, projection)
            joint = 0.62 * state + 0.38 * effect
            if joint > best_joint:
                best_joint = joint
                best_state = state
                best_effect = effect
        return best_state, best_effect

    @staticmethod
    def _aggregate_projection(items: Sequence[_PendingObservation]) -> EpisodicProjection:
        if not items:
            return EpisodicProjection()
        sense_counts = Counter(token for item in items for token in item.projection.sense_ids)
        concept_counts = Counter(token for item in items for token in item.projection.concept_ids)
        internal_counts = Counter(token for item in items for token in item.projection.internal_tokens)
        effect_counts = Counter(token for item in items for token in item.projection.effect_features)
        action_counts = Counter(
            item.projection.action_token
            for item in items
            if item.projection.action_token is not None
        )

        def top(counter: Counter[str], limit: int) -> tuple[str, ...]:
            return tuple(token for token, _ in counter.most_common(limit))

        action = action_counts.most_common(1)[0][0] if action_counts else None
        return EpisodicProjection(
            sense_ids=top(sense_counts, 16),
            concept_ids=top(concept_counts, 8),
            internal_tokens=top(internal_counts, 8),
            action_token=action,
            effect_features=top(effect_counts, 16),
        )

    def _boundary_before(self, projection: EpisodicProjection, tick: int) -> bool:
        if not self._pending:
            return False
        previous = self._pending[-1]
        if len(self._pending) >= self._limits.max_episodic_episode_records:
            return True
        if tick > previous.record.tick_class + 1:
            return True
        if projection.action_token != previous.projection.action_token:
            return True
        if self.projection_similarity(projection, previous.projection) < 0.34:
            return True
        return False

    def observe(
        self,
        record: ExperienceRecord,
        projection: EpisodicProjection | None = None,
    ) -> str | None:
        if not isinstance(record, ExperienceRecord):
            raise EpisodicMemoryError("record must be ExperienceRecord")
        if record.organism_id != self._organism_id:
            raise EpisodicMemoryError("experience belongs to another organism")
        if not _is_causal_observation(record):
            return None

        selected = projection or EpisodicProjection.from_record(record)
        if selected.action_token is None and record.action_token is not None:
            selected = EpisodicProjection(
                sense_ids=selected.sense_ids,
                concept_ids=selected.concept_ids,
                internal_tokens=selected.internal_tokens,
                action_token=record.action_token,
                effect_features=selected.effect_features,
            )
        if not selected.effect_features:
            selected = selected.with_effects(record.outcome_tokens)

        finalized: str | None = None
        if self._boundary_before(selected, record.tick_class):
            finalized = self.flush()
        self._pending.append(_PendingObservation(record=record, projection=selected))
        if len(self._pending) >= self._limits.max_episodic_episode_records:
            finalized = self.flush()
        return finalized

    def flush(self) -> str | None:
        if not self._pending:
            return None
        items = tuple(self._pending)
        self._pending.clear()
        projection = self._aggregate_projection(items)
        start_tick = items[0].record.tick_class
        end_tick = items[-1].record.tick_class
        occurrence_tick = start_tick

        steps = tuple(
            EpisodeStep(
                tick_offset=max(0, item.record.tick_class - start_tick),
                source_record_id=item.record.record_id,
                source_content_hash=item.record.content_hash,
                evidence_refs=_bounded_unique(item.record.evidence_refs, limit=8),
                source_kind=item.record.source_kind,
            )
            for item in items[:8]
        )
        sources = _bounded_unique(
            (item.record.record_id for item in items),
            limit=32,
        )
        evidence = _bounded_unique(
            (ref for item in items for ref in item.record.evidence_refs),
            limit=32,
        )

        best_index: int | None = None
        best_score = -1.0
        for index, episode in enumerate(self._episodes):
            current = episode.projection
            if current.action_token != projection.action_token:
                continue
            state_similarity, effect_similarity = self._family_match(
                episode,
                projection,
            )
            if (
                state_similarity < self._STATE_FAMILY_THRESHOLD
                or effect_similarity < self._EFFECT_FAMILY_THRESHOLD
            ):
                continue
            score = 0.62 * state_similarity + 0.38 * effect_similarity
            if score > best_score:
                best_score = score
                best_index = index

        if best_index is None:
            novelty = self._novelty_for(projection)
            surprise = self._surprise_for(projection)
            material = (
                f"{self._organism_id}|{projection.action_token}|"
                f"{projection.sense_ids}|{projection.concept_ids}|"
                f"{projection.effect_features}|{start_tick}"
            )
            episode = ExperienceEpisode(
                episode_id="episode." + hashlib.sha256(material.encode()).hexdigest()[:32],
                start_tick=start_tick,
                end_tick=end_tick,
                occurrence_ticks=(occurrence_tick,),
                trace=steps,
                action_token=projection.action_token,
                sense_support={token: 1 for token in projection.sense_ids},
                concept_support={token: 1 for token in projection.concept_ids},
                internal_support={token: 1 for token in projection.internal_tokens},
                effect_support={token: 1 for token in projection.effect_features},
                exceptions=(),
                evidence_refs=evidence,
                source_record_ids=sources,
                novelty=novelty,
                surprise=surprise,
            )
            self._episodes.append(episode)
            episode_id = episode.episode_id
        else:
            episode = self._episodes[best_index]
            self._merge_occurrence(
                episode,
                projection=projection,
                start_tick=start_tick,
                end_tick=end_tick,
                occurrence_tick=occurrence_tick,
                steps=steps,
                evidence=evidence,
                sources=sources,
                state_similarity=self.projection_similarity(
                    episode.projection,
                    projection,
                ),
                effect_similarity=self._effect_similarity(
                    episode.projection,
                    projection,
                ),
            )
            episode_id = episode.episode_id
            self._compaction_count += 1

        self._enforce_capacity()
        self.consolidate()
        return episode_id

    @staticmethod
    def _bounded_support_merge(
        support: dict[str, int],
        values: Sequence[str],
        *,
        maximum: int,
    ) -> None:
        for token in values:
            support[token] = support.get(token, 0) + 1
        if len(support) > maximum:
            ranked = sorted(support.items(), key=lambda item: (-item[1], item[0]))
            support.clear()
            support.update(ranked[:maximum])

    def _merge_occurrence(
        self,
        episode: ExperienceEpisode,
        *,
        projection: EpisodicProjection,
        start_tick: int,
        end_tick: int,
        occurrence_tick: int,
        steps: tuple[EpisodeStep, ...],
        evidence: tuple[str, ...],
        sources: tuple[str, ...],
        state_similarity: float,
        effect_similarity: float,
    ) -> None:
        episode.recurrence += 1
        episode.compressed = True
        episode.end_tick = max(episode.end_tick, end_tick)
        occurrence_values = sorted(set((*episode.occurrence_ticks, occurrence_tick)))
        if len(occurrence_values) > 64:
            occurrence_values = [*occurrence_values[:32], *occurrence_values[-32:]]
        episode.occurrence_ticks = tuple(occurrence_values)
        self._bounded_support_merge(episode.sense_support, projection.sense_ids, maximum=32)
        self._bounded_support_merge(episode.concept_support, projection.concept_ids, maximum=16)
        self._bounded_support_merge(episode.internal_support, projection.internal_tokens, maximum=16)
        self._bounded_support_merge(episode.effect_support, projection.effect_features, maximum=32)

        if state_similarity < 0.66 or effect_similarity < 0.60:
            is_new_exception = all(
                self.projection_similarity(existing, projection, include_effect=True) < 0.85
                for existing in episode.exceptions
            )
            if is_new_exception:
                exceptions = (*episode.exceptions, projection)
                if len(exceptions) > 4:
                    exceptions = exceptions[-4:]
                episode.exceptions = tuple(exceptions)

        # Keep a few provenance exemplars, biased toward temporal diversity.
        combined_steps = list(episode.trace)
        for step in steps:
            absolute_tick = start_tick + step.tick_offset
            if any(
                abs((episode.start_tick + existing.tick_offset) - absolute_tick)
                < self._limits.episodic_epoch_ticks
                for existing in combined_steps
            ):
                continue
            shifted = EpisodeStep(
                tick_offset=max(0, absolute_tick - episode.start_tick),
                source_record_id=step.source_record_id,
                source_content_hash=step.source_content_hash,
                evidence_refs=step.evidence_refs,
                source_kind=step.source_kind,
            )
            combined_steps.append(shifted)
            if len(combined_steps) >= 8:
                break
        episode.trace = tuple(sorted(combined_steps, key=lambda item: item.tick_offset)[:8])
        episode.evidence_refs = _bounded_unique((*episode.evidence_refs, *evidence), limit=32)
        episode.source_record_ids = _bounded_unique((*episode.source_record_ids, *sources), limit=32)
        episode.novelty = max(episode.novelty, self._novelty_for(projection))
        episode.surprise = max(episode.surprise, self._surprise_for(projection))

    def _novelty_for(self, projection: EpisodicProjection) -> float:
        if not self._episodes:
            return 1.0
        best = max(
            self.projection_similarity(episode.projection, projection)
            for episode in self._episodes
        )
        return max(0.0, min(1.0, 1.0 - best))

    def _surprise_for(self, projection: EpisodicProjection) -> float:
        if not self._episodes:
            return 1.0
        compatible = [
            self._effect_similarity(episode.projection, projection)
            for episode in self._episodes
            if episode.action_token == projection.action_token
        ]
        if not compatible:
            return 1.0
        return max(0.0, min(1.0, 1.0 - max(compatible)))

    def _estimated_size(self) -> int:
        return len(
            json.dumps(
                self._checkpoint_payload(include_pending=False),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )

    def _least_informative_index(self) -> int:
        newest = max((episode.end_tick for episode in self._episodes), default=0)

        def score(item: tuple[int, ExperienceEpisode]) -> tuple[float, int, str]:
            index, episode = item
            age = max(0, newest - episode.end_tick)
            recurrence = min(1.0, episode.recurrence / 8.0)
            retrieval = min(1.0, self._retrieval_counts.get(episode.episode_id, 0) / 8.0)
            keep = 0.35 * episode.novelty + 0.35 * episode.surprise + 0.20 * recurrence + 0.10 * retrieval
            return keep, -age, episode.episode_id

        return min(enumerate(self._episodes), key=score)[0]

    def _enforce_capacity(self) -> None:
        while (
            len(self._episodes) > self._limits.max_episodic_episodes
            or self._estimated_size() > self._limits.max_episodic_checkpoint_bytes
        ):
            if not self._episodes:
                raise EpisodicMemoryError("episodic memory cannot satisfy kernel budget")
            victim = self._least_informative_index()
            episode = self._episodes.pop(victim)
            self._interpretations.pop(episode.episode_id, None)
            self._retrieval_counts.pop(episode.episode_id, None)
            self._eviction_count += 1

    def retrieve(
        self,
        context_tokens: Sequence[str] | EpisodicProjection,
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[EpisodeMatch, ...]:
        if isinstance(context_tokens, EpisodicProjection):
            query = context_tokens
        else:
            query = EpisodicProjection(
                sense_ids=_bounded_unique(
                    (
                        token.removeprefix("sense.")
                        for token in context_tokens
                        if str(token).startswith("sense.")
                    ),
                    limit=16,
                ),
                concept_ids=_bounded_unique(
                    (
                        token.removeprefix("concept.")
                        for token in context_tokens
                        if str(token).startswith("concept.")
                    ),
                    limit=8,
                ),
                internal_tokens=_bounded_unique(
                    (str(token) for token in context_tokens if str(token).startswith("internal.")),
                    limit=8,
                ),
                action_token=action_token,
            )
        limit = self._limits.max_episodic_retrieval_candidates if k is None else int(k)
        if not 1 <= limit <= self._limits.max_episodic_retrieval_candidates:
            raise EpisodicMemoryError("retrieval k exceeds kernel limit")

        matches: list[EpisodeMatch] = []
        for episode in self._episodes:
            if action_token is not None and episode.action_token != action_token:
                continue
            similarity = max(
                self.projection_similarity(candidate, query)
                for candidate in (episode.projection, *episode.exceptions)
            )
            if similarity <= 0.0:
                continue
            matches.append(
                EpisodeMatch(
                    episode_id=episode.episode_id,
                    similarity=similarity,
                    episode=episode,
                    interpretations=self.interpretations_for(episode.episode_id),
                )
            )
        matches.sort(
            key=lambda item: (
                -item.similarity,
                -item.episode.recurrence,
                -item.episode.surprise,
                item.episode_id,
            )
        )
        selected = tuple(matches[:limit])
        self._retrieval_count += 1
        for match in selected:
            self._retrieval_counts[match.episode_id] += 1
        return selected

    def reinterpret(
        self,
        representation_id: str,
        support_tokens: Sequence[str],
        *,
        min_overlap: float = 0.5,
    ) -> int:
        if not _valid_token(representation_id):
            raise EpisodicMemoryError("invalid representation id")
        if not 0.0 < min_overlap <= 1.0:
            raise EpisodicMemoryError("invalid reinterpretation threshold")
        support = set(_bounded_unique((str(token) for token in support_tokens), limit=32))
        if not support:
            return 0
        changed = 0
        for episode in self._episodes:
            factual = set(episode.projection.context_tokens) | set(episode.projection.effect_features)
            indexed = factual | self._interpretations.get(episode.episode_id, set())
            if len(indexed & support) / len(support) < min_overlap:
                continue
            bucket = self._interpretations.setdefault(episode.episode_id, set())
            if representation_id in bucket:
                continue
            if len(bucket) >= self._limits.max_episodic_interpretations_per_episode:
                continue
            bucket.add(representation_id)
            changed += 1
        return changed

    def consolidate(self) -> tuple[ConsolidatedContingency, ...]:
        consolidated: dict[str, ConsolidatedContingency] = {}
        for episode in self._episodes:
            epochs = {
                tick // self._limits.episodic_epoch_ticks
                for tick in episode.occurrence_ticks
            }
            if len(epochs) < self._limits.episodic_min_consolidation_epochs:
                continue
            projection = episode.projection
            material = f"{episode.episode_id}|{episode.action_token}"
            contingency_id = "contingency." + hashlib.sha256(material.encode()).hexdigest()[:32]
            confidence = min(
                1.0,
                0.5 * min(1.0, len(epochs) / 6.0)
                + 0.5 * min(1.0, episode.recurrence / 8.0),
            )
            consolidated[contingency_id] = ConsolidatedContingency(
                contingency_id=contingency_id,
                context_tokens=projection.context_tokens,
                sense_ids=projection.sense_ids,
                concept_ids=projection.concept_ids,
                action_token=episode.action_token,
                outcome_tokens=projection.effect_features,
                support_episode_ids=(episode.episode_id,),
                support_epochs=len(epochs),
                confidence=confidence,
            )
        self._consolidated = consolidated
        return self.consolidated

    def predict(
        self,
        context_tokens: Sequence[str] | EpisodicProjection,
        *,
        action_token: str | None,
        k: int | None = None,
    ) -> EpisodicPrediction | None:
        matches = self.retrieve(context_tokens, action_token=action_token, k=k)
        if not matches:
            return None
        votes: Counter[str] = Counter()
        total = 0.0
        support_ids: list[str] = []
        for match in matches:
            weight = max(1e-9, match.similarity) * max(1, match.episode.recurrence)
            total += weight
            support_ids.append(match.episode_id)
            for outcome in match.episode.projection.effect_features:
                votes[outcome] += weight
        if not votes or total <= 0:
            return None
        ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
        best = ranked[0][1]
        predicted = tuple(token for token, weight in ranked if weight >= 0.5 * best)[:16]
        return EpisodicPrediction(
            action_token=action_token,
            predicted_outcomes=predicted,
            confidence=min(1.0, best / total),
            support_episode_ids=tuple(support_ids),
        )

    def cognitive_replay(
        self,
        context_tokens: Sequence[str] | EpisodicProjection,
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[CognitiveReplay, ...]:
        limit = self._limits.max_episodic_replay_items if k is None else int(k)
        if not 1 <= limit <= self._limits.max_episodic_replay_items:
            raise EpisodicMemoryError("replay k exceeds kernel limit")
        matches = self.retrieve(context_tokens, action_token=action_token, k=limit)
        result = tuple(
            CognitiveReplay(
                episode_id=match.episode_id,
                similarity=match.similarity,
                trace=match.episode.trace,
                context_tokens=match.episode.projection.context_tokens,
                action_tokens=match.episode.action_tokens,
                outcome_tokens=match.episode.outcome_tokens,
                interpretations=match.interpretations,
            )
            for match in matches
        )
        if result:
            self._replay_count += 1
        return result

    def replay_records(self, *, max_records: int = 8192) -> tuple[ExperienceRecord, ...]:
        """v2 deliberately does not reconstruct raw records from compact memory.

        The causal ExperienceLedger remains authoritative for private-model
        training. Episodic memory preserves provenance hashes/references rather
        than duplicating telemetry-sized raw state.
        """
        _ = max_records
        return ()

    def metrics(self, *, current_tick: int) -> EpisodicMemoryMetrics:
        ages = [max(0, current_tick - episode.end_tick) for episode in self._episodes]
        return EpisodicMemoryMetrics(
            episode_count=len(self._episodes),
            pending_records=len(self._pending),
            compressed_episode_count=sum(episode.recurrence > 1 for episode in self._episodes),
            interpretation_count=sum(len(values) for values in self._interpretations.values()),
            consolidated_contingencies=len(self._consolidated),
            retrieval_count=self._retrieval_count,
            replay_count=self._replay_count,
            compaction_count=self._compaction_count,
            eviction_count=self._eviction_count,
            oldest_episode_age=max(ages, default=0),
            mean_episode_age=(sum(ages) / len(ages) if ages else 0.0),
        )

    def _checkpoint_payload(self, *, include_pending: bool) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self._organism_id,
            "episodes": [episode.checkpoint() for episode in self._episodes],
            "interpretations": {
                episode_id: sorted(values)
                for episode_id, values in sorted(self._interpretations.items())
                if values
            },
            "retrieval_counts": dict(sorted(self._retrieval_counts.items())),
            "metrics": {
                "retrieval_count": self._retrieval_count,
                "replay_count": self._replay_count,
                "compaction_count": self._compaction_count,
                "eviction_count": self._eviction_count,
            },
        }
        if include_pending:
            payload["pending"] = [
                {
                    "tick": item.record.tick_class,
                    "record_id": item.record.record_id,
                    "content_hash": item.record.content_hash,
                    "evidence_refs": list(item.record.evidence_refs[:8]),
                    "source_kind": item.record.source_kind.value,
                    "projection": item.projection.checkpoint(),
                }
                for item in self._pending
            ]
        return payload

    def checkpoint(self) -> dict[str, object]:
        # A restart is a causal discontinuity. Pending observations remain
        # ephemeral and are deliberately not bridged across checkpoints.
        payload = self._checkpoint_payload(include_pending=False)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        if len(encoded) > self._limits.max_episodic_checkpoint_bytes:
            raise EpisodicMemoryError("episodic checkpoint exceeds kernel byte limit")
        return payload

    @classmethod
    def _restore_v1(
        cls,
        payload: Mapping[str, object],
        *,
        organism_id: str,
        kernel_limits: KernelLimits,
    ) -> "EpisodicExperienceMemory":
        memory = cls(organism_id, kernel_limits=kernel_limits)
        raw_episodes = payload.get("episodes", [])
        if not isinstance(raw_episodes, list):
            raise EpisodicMemoryError("invalid v1 episode collection")
        for raw in raw_episodes:
            if not isinstance(raw, Mapping):
                continue
            initial = raw.get("initial_context", [])
            actions = raw.get("action_tokens", [])
            outcomes = raw.get("outcome_tokens", [])
            sources = raw.get("source_record_ids", [])
            evidence = raw.get("evidence_refs", [])
            if not all(isinstance(value, list) for value in (initial, actions, outcomes, sources, evidence)):
                continue
            pseudo_record = ExperienceRecord(
                record_id=(
                    str(sources[0])
                    if sources
                    else "transition.migrated." + hashlib.sha256(str(raw).encode()).hexdigest()[:24]
                ),
                organism_id=organism_id,
                tick_class=max(0, int(raw.get("start_tick", 0))),
                context_tokens=tuple(str(item) for item in initial[:256]),
                action_token=(str(actions[0]) if actions else None),
                outcome_tokens=tuple(str(item) for item in outcomes[:32]) or ("outcome.migrated",),
                epistemic_status=EpistemicStatus.OBSERVED,
                evidence_refs=tuple(str(item) for item in evidence[:16]) or ("evidence.migrated",),
                confidence_class=7,
                source_kind=SourceKind.ACTION_OUTCOME,
            )
            projection = EpisodicProjection.from_record(pseudo_record)
            memory.observe(pseudo_record, projection)
            memory.flush()
        memory._interpretations = {}
        return memory

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
        *,
        organism_id: str,
        kernel_limits: KernelLimits | None = None,
    ) -> "EpisodicExperienceMemory":
        limits = kernel_limits or KernelLimits()
        if payload is None:
            return cls(organism_id, kernel_limits=limits)
        if not isinstance(payload, Mapping):
            raise EpisodicMemoryError("invalid episodic checkpoint")
        schema = payload.get("schema_version")
        if schema == 1:
            return cls._restore_v1(payload, organism_id=organism_id, kernel_limits=limits)
        if schema != cls.SCHEMA_VERSION or payload.get("organism_id") != organism_id:
            raise EpisodicMemoryError("invalid episodic checkpoint identity")

        memory = cls(organism_id, kernel_limits=limits)
        raw_episodes = payload.get("episodes", [])
        if not isinstance(raw_episodes, list) or len(raw_episodes) > limits.max_episodic_episodes:
            raise EpisodicMemoryError("invalid episodic episode collection")
        memory._episodes = [
            ExperienceEpisode.restore(raw)
            for raw in raw_episodes
            if isinstance(raw, Mapping)
        ]
        if len(memory._episodes) != len(raw_episodes):
            raise EpisodicMemoryError("invalid episode checkpoint entry")
        ids = [episode.episode_id for episode in memory._episodes]
        if len(ids) != len(set(ids)):
            raise EpisodicMemoryError("duplicate episodic episode id")

        raw_interpretations = payload.get("interpretations", {})
        if not isinstance(raw_interpretations, Mapping):
            raise EpisodicMemoryError("invalid episodic interpretations")
        for episode_id, raw_values in raw_interpretations.items():
            if episode_id not in set(ids) or not isinstance(raw_values, list):
                continue
            values = _bounded_unique(
                (str(value) for value in raw_values),
                limit=limits.max_episodic_interpretations_per_episode,
            )
            if values:
                memory._interpretations[str(episode_id)] = set(values)

        raw_counts = payload.get("retrieval_counts", {})
        if isinstance(raw_counts, Mapping):
            for episode_id, count in raw_counts.items():
                if episode_id in set(ids) and isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                    memory._retrieval_counts[str(episode_id)] = count

        raw_metrics = payload.get("metrics", {})
        if isinstance(raw_metrics, Mapping):
            for name in ("retrieval_count", "replay_count", "compaction_count", "eviction_count"):
                value = raw_metrics.get(name, 0)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    setattr(memory, f"_{name}", value)

        # Pending observations are intentionally absent from v2 checkpoints.
        memory.consolidate()
        memory._enforce_capacity()
        return memory


__all__ = [
    "CognitiveReplay",
    "ConsolidatedContingency",
    "EpisodeMatch",
    "EpisodeStep",
    "EpisodicExperienceMemory",
    "EpisodicMemoryError",
    "EpisodicMemoryMetrics",
    "EpisodicPrediction",
    "EpisodicProjection",
    "ExperienceEpisode",
]
