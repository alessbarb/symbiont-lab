from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence

from ..cognition.limits import KernelLimits
from .experience import EpistemicStatus, ExperienceRecord, SourceKind


_HARD_MAX_EPISODE_STEPS = 256


class EpisodicMemoryError(ValueError):
    """Raised when episodic state is invalid or exceeds kernel limits."""


def _valid_opaque_string(value: object, *, max_length: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= max_length
        and all(0x21 <= ord(char) <= 0x7E for char in value)
    )


def _validate_opaque_tuple(
    values: tuple[str, ...],
    *,
    maximum: int,
    max_length: int = 96,
    field: str,
) -> None:
    if not isinstance(values, tuple) or len(values) > maximum:
        raise EpisodicMemoryError(f"{field} exceeds its token bound")
    if any(
        not _valid_opaque_string(value, max_length=max_length)
        for value in values
    ):
        raise EpisodicMemoryError(f"{field} contains an invalid opaque token")


def _bounded_tokens(values: Iterable[str], *, limit: int = 256) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw)
        if not value or value in seen:
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
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _is_causal_observation(record: ExperienceRecord) -> bool:
    return (
        record.record_id.startswith("transition.")
        and record.epistemic_status is EpistemicStatus.OBSERVED
        and record.source_kind is not SourceKind.MODEL
    )


@dataclass(slots=True, frozen=True)
class EpisodeStep:
    """One bounded, organism-native step inside an episodic trace."""

    tick_offset: int
    source_record_id: str
    context_tokens: tuple[str, ...]
    action_token: str | None
    outcome_tokens: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence_class: int
    source_kind: SourceKind

    def __post_init__(self) -> None:
        if (
            isinstance(self.tick_offset, bool)
            or not isinstance(self.tick_offset, int)
            or self.tick_offset < 0
        ):
            raise EpisodicMemoryError("tick_offset must be a non-negative integer")
        if (
            not isinstance(self.source_record_id, str)
            or not self.source_record_id
            or len(self.source_record_id) > 128
        ):
            raise EpisodicMemoryError("invalid episode step source record id")
        if len(self.context_tokens) > 256 or len(self.outcome_tokens) > 32:
            raise EpisodicMemoryError("episode step exceeds token bound")
        if len(self.evidence_refs) > 16:
            raise EpisodicMemoryError("episode step exceeds evidence bound")
        if (
            isinstance(self.confidence_class, bool)
            or not isinstance(self.confidence_class, int)
            or not 0 <= self.confidence_class <= 7
        ):
            raise EpisodicMemoryError("invalid episode step confidence class")
        if not isinstance(self.source_kind, SourceKind) or self.source_kind is SourceKind.MODEL:
            raise EpisodicMemoryError("invalid episode step source kind")
        if self.action_token is not None and (
            not isinstance(self.action_token, str)
            or not self.action_token
            or len(self.action_token) > 96
        ):
            raise EpisodicMemoryError("invalid episode step action token")
        try:
            ExperienceRecord(
                record_id=self.source_record_id,
                organism_id="episodic-validation",
                tick_class=self.tick_offset,
                context_tokens=self.context_tokens,
                action_token=self.action_token,
                outcome_tokens=self.outcome_tokens,
                epistemic_status=EpistemicStatus.OBSERVED,
                evidence_refs=self.evidence_refs,
                confidence_class=self.confidence_class,
                source_kind=self.source_kind,
            )
        except ValueError as exc:
            raise EpisodicMemoryError("invalid factual episode step") from exc

    def to_experience_record(
        self,
        *,
        organism_id: str,
        episode_start_tick: int,
    ) -> ExperienceRecord:
        """Reconstruct the original bounded factual record for cognitive replay."""
        return ExperienceRecord(
            record_id=self.source_record_id,
            organism_id=organism_id,
            tick_class=episode_start_tick + self.tick_offset,
            context_tokens=self.context_tokens,
            action_token=self.action_token,
            outcome_tokens=self.outcome_tokens,
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=self.evidence_refs,
            confidence_class=self.confidence_class,
            source_kind=self.source_kind,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "tick_offset": self.tick_offset,
            "source_record_id": self.source_record_id,
            "context_tokens": list(self.context_tokens),
            "action_token": self.action_token,
            "outcome_tokens": list(self.outcome_tokens),
            "evidence_refs": list(self.evidence_refs),
            "confidence_class": self.confidence_class,
            "source_kind": self.source_kind.value,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "EpisodeStep":
        try:
            tick_offset = payload["tick_offset"]
            source_record_id = payload["source_record_id"]
            raw_context = payload["context_tokens"]
            raw_outcomes = payload["outcome_tokens"]
            raw_evidence = payload["evidence_refs"]
            confidence_class = payload["confidence_class"]
            raw_source_kind = payload["source_kind"]
            action = payload.get("action_token")
            if (
                isinstance(tick_offset, bool)
                or not isinstance(tick_offset, int)
                or not isinstance(source_record_id, str)
                or not source_record_id
                or not isinstance(raw_context, list)
                or not isinstance(raw_outcomes, list)
                or not isinstance(raw_evidence, list)
                or any(not isinstance(item, str) or not item for item in raw_context)
                or any(not isinstance(item, str) or not item for item in raw_outcomes)
                or any(not isinstance(item, str) or not item for item in raw_evidence)
                or isinstance(confidence_class, bool)
                or not isinstance(confidence_class, int)
                or not isinstance(raw_source_kind, str)
                or (action is not None and not isinstance(action, str))
            ):
                raise EpisodicMemoryError("invalid episode step checkpoint")
            return cls(
                tick_offset=tick_offset,
                source_record_id=source_record_id,
                context_tokens=tuple(raw_context),
                action_token=action,
                outcome_tokens=tuple(raw_outcomes),
                evidence_refs=tuple(raw_evidence),
                confidence_class=confidence_class,
                source_kind=SourceKind(raw_source_kind),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, EpisodicMemoryError):
                raise
            raise EpisodicMemoryError("invalid episode step checkpoint") from exc


@dataclass(slots=True, frozen=True)
class ExperienceEpisode:
    """Immutable factual core of one bounded lived episode.

    The episode stores only organism-native opaque tokens already present in
    ExperienceRecord. Interpretations are deliberately stored elsewhere so a
    later concept can reinterpret the past without rewriting what happened.
    """

    episode_id: str
    start_tick: int
    end_tick: int
    occurrence_ticks: tuple[int, ...]
    trace: tuple[EpisodeStep, ...]
    initial_context: tuple[str, ...]
    terminal_context: tuple[str, ...]
    action_tokens: tuple[str, ...]
    outcome_tokens: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    novelty: float
    surprise: float
    recurrence: int = 1
    compressed: bool = False

    def __post_init__(self) -> None:
        if not _valid_opaque_string(self.episode_id, max_length=128):
            raise EpisodicMemoryError("episode_id must be a bounded non-empty identifier")
        if (
            isinstance(self.start_tick, bool)
            or not isinstance(self.start_tick, int)
            or isinstance(self.end_tick, bool)
            or not isinstance(self.end_tick, int)
            or self.start_tick < 0
            or self.end_tick < self.start_tick
        ):
            raise EpisodicMemoryError("invalid episode tick range")
        if (
            not self.occurrence_ticks
            or len(self.occurrence_ticks) > 64
            or any(
                isinstance(tick, bool)
                or not isinstance(tick, int)
                or tick < 0
                for tick in self.occurrence_ticks
            )
            or tuple(sorted(set(self.occurrence_ticks))) != self.occurrence_ticks
            or self.occurrence_ticks[0] != self.start_tick
            or any(tick > self.end_tick for tick in self.occurrence_ticks)
        ):
            raise EpisodicMemoryError("invalid episode occurrence ticks")
        if not self.trace:
            raise EpisodicMemoryError("episode trace must not be empty")
        if len(self.trace) > _HARD_MAX_EPISODE_STEPS:
            raise EpisodicMemoryError("episode trace exceeds hard step bound")
        if any(not isinstance(step, EpisodeStep) for step in self.trace):
            raise EpisodicMemoryError("episode trace must contain EpisodeStep values")
        _validate_opaque_tuple(
            self.initial_context,
            maximum=256,
            field="initial_context",
        )
        _validate_opaque_tuple(
            self.terminal_context,
            maximum=256,
            field="terminal_context",
        )
        _validate_opaque_tuple(
            self.action_tokens,
            maximum=64,
            field="action_tokens",
        )
        _validate_opaque_tuple(
            self.outcome_tokens,
            maximum=128,
            field="outcome_tokens",
        )
        _validate_opaque_tuple(
            self.evidence_refs,
            maximum=64,
            field="evidence_refs",
        )
        _validate_opaque_tuple(
            self.source_record_ids,
            maximum=64,
            max_length=128,
            field="source_record_ids",
        )
        trace_offsets = tuple(step.tick_offset for step in self.trace)
        if tuple(sorted(trace_offsets)) != trace_offsets:
            raise EpisodicMemoryError("episode trace must be temporally ordered")
        if self.start_tick + max(trace_offsets) > self.end_tick:
            raise EpisodicMemoryError("episode trace exceeds episode tick range")
        for field_name in ("novelty", "surprise"):
            value = getattr(self, field_name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise EpisodicMemoryError(f"{field_name} must be within [0, 1]")
        if (
            isinstance(self.recurrence, bool)
            or not isinstance(self.recurrence, int)
            or self.recurrence < len(self.occurrence_ticks)
        ):
            raise EpisodicMemoryError("recurrence must cover retained occurrences")
        if not isinstance(self.compressed, bool):
            raise EpisodicMemoryError("compressed must be boolean")

    def checkpoint(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "occurrence_ticks": list(self.occurrence_ticks),
            "trace": [step.checkpoint() for step in self.trace],
            "initial_context": list(self.initial_context),
            "terminal_context": list(self.terminal_context),
            "action_tokens": list(self.action_tokens),
            "outcome_tokens": list(self.outcome_tokens),
            "evidence_refs": list(self.evidence_refs),
            "source_record_ids": list(self.source_record_ids),
            "novelty": self.novelty,
            "surprise": self.surprise,
            "recurrence": self.recurrence,
            "compressed": self.compressed,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "ExperienceEpisode":
        try:
            def strings(
                name: str,
                maximum: int,
                *,
                max_length: int = 96,
            ) -> tuple[str, ...]:
                raw = payload[name]
                if not isinstance(raw, list) or len(raw) > maximum:
                    raise EpisodicMemoryError(f"invalid {name}")
                values = tuple(raw)
                _validate_opaque_tuple(
                    values,
                    maximum=maximum,
                    max_length=max_length,
                    field=name,
                )
                return values

            episode_id = payload["episode_id"]
            start_tick = payload["start_tick"]
            end_tick = payload["end_tick"]
            recurrence = payload.get("recurrence", 1)
            compressed = payload.get("compressed", False)
            raw_occurrence_ticks = payload["occurrence_ticks"]
            raw_trace = payload["trace"]
            if (
                not isinstance(episode_id, str)
                or not episode_id
                or isinstance(start_tick, bool)
                or not isinstance(start_tick, int)
                or isinstance(end_tick, bool)
                or not isinstance(end_tick, int)
                or isinstance(recurrence, bool)
                or not isinstance(recurrence, int)
                or not isinstance(compressed, bool)
                or not isinstance(raw_occurrence_ticks, list)
                or not raw_occurrence_ticks
                or len(raw_occurrence_ticks) > 64
                or any(
                    isinstance(tick, bool)
                    or not isinstance(tick, int)
                    or tick < 0
                    for tick in raw_occurrence_ticks
                )
                or raw_occurrence_ticks != sorted(set(raw_occurrence_ticks))
                or not isinstance(raw_trace, list)
                or not raw_trace
                or len(raw_trace) > _HARD_MAX_EPISODE_STEPS
                or any(not isinstance(item, Mapping) for item in raw_trace)
            ):
                raise EpisodicMemoryError("invalid episodic episode checkpoint")
            raw_novelty = payload["novelty"]
            raw_surprise = payload["surprise"]
            if (
                isinstance(raw_novelty, bool)
                or not isinstance(raw_novelty, (int, float))
                or isinstance(raw_surprise, bool)
                or not isinstance(raw_surprise, (int, float))
            ):
                raise EpisodicMemoryError("invalid episodic novelty/surprise")
            return cls(
                episode_id=episode_id,
                start_tick=start_tick,
                end_tick=end_tick,
                occurrence_ticks=tuple(raw_occurrence_ticks),
                trace=tuple(EpisodeStep.restore(item) for item in raw_trace),
                initial_context=strings("initial_context", 256),
                terminal_context=strings("terminal_context", 256),
                action_tokens=strings("action_tokens", 64),
                outcome_tokens=strings("outcome_tokens", 128),
                evidence_refs=strings("evidence_refs", 64),
                source_record_ids=strings(
                    "source_record_ids",
                    64,
                    max_length=128,
                ),
                novelty=float(raw_novelty),
                surprise=float(raw_surprise),
                recurrence=recurrence,
                compressed=compressed,
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, EpisodicMemoryError):
                raise
            raise EpisodicMemoryError("invalid episodic episode checkpoint") from exc


@dataclass(slots=True, frozen=True)
class EpisodeMatch:
    episode_id: str
    similarity: float
    episode: ExperienceEpisode
    interpretations: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ConsolidatedContingency:
    contingency_id: str
    context_tokens: tuple[str, ...]
    action_token: str | None
    outcome_tokens: tuple[str, ...]
    support_episode_ids: tuple[str, ...]
    support_epochs: int
    confidence: float


@dataclass(slots=True, frozen=True)
class EpisodicPrediction:
    action_token: str | None
    predicted_outcomes: tuple[str, ...]
    confidence: float
    support_episode_ids: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CognitiveReplay:
    episode_id: str
    similarity: float
    trace: tuple[EpisodeStep, ...]
    context_tokens: tuple[str, ...]
    action_tokens: tuple[str, ...]
    outcome_tokens: tuple[str, ...]
    interpretations: tuple[str, ...]


@dataclass(slots=True, frozen=True)
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


class EpisodicExperienceMemory:
    """Bounded, reinterpretable long-horizon memory owned by one organism.

    ExperienceLedger remains the append-only causal evidence stream used by
    private-model training. This layer turns independently observed transition
    records into temporally segmented episodes, supports retrieval from present
    context, preserves immutable factual cores while interpretations evolve,
    and derives multi-epoch contingencies without external semantics.

    No method executes a motor action or consumes evaluator labels.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        organism_id: str,
        *,
        kernel_limits: KernelLimits | None = None,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id or len(organism_id) > 128:
            raise EpisodicMemoryError("organism_id must be a bounded non-empty string")
        self._organism_id = organism_id
        self._limits = kernel_limits or KernelLimits()
        self._episodes: list[ExperienceEpisode] = []
        self._pending: list[ExperienceRecord] = []
        self._interpretations: dict[str, set[str]] = {}
        self._retrieval_counts: Counter[str] = Counter()
        self._consolidated: dict[str, ConsolidatedContingency] = {}
        self._episode_payload_bytes: dict[str, int] = {}
        self._pending_payload_bytes = 0
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
    def _json_size(payload: object) -> int:
        return len(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )

    def _episode_size(self, episode: ExperienceEpisode) -> int:
        return self._json_size(episode.checkpoint())

    def _record_size(self, record: ExperienceRecord) -> int:
        return self._json_size(record.canonical_payload())

    def _estimated_persisted_size(self) -> int:
        # Conservative structural allowance covers list/map separators,
        # retrieval counters and metrics without serializing the whole memory.
        interpretation_bytes = sum(
            64
            + len(episode_id)
            + sum(len(value) + 8 for value in values)
            for episode_id, values in self._interpretations.items()
        )
        structural_allowance = 1_024 + 128 * len(self._episodes)
        return (
            structural_allowance
            + sum(self._episode_payload_bytes.values())
            + self._pending_payload_bytes
            + interpretation_bytes
        )

    @staticmethod
    def _record_context(record: ExperienceRecord) -> tuple[str, ...]:
        return record.context_tokens

    @staticmethod
    def _action_regime(record: ExperienceRecord) -> str:
        return "action" if record.action_token is not None else "passive"

    def _boundary_before(self, record: ExperienceRecord) -> bool:
        if not self._pending:
            return False
        previous = self._pending[-1]
        if len(self._pending) >= self._limits.max_episodic_episode_records:
            return True
        if record.tick_class > previous.tick_class + 1:
            return True
        if self._action_regime(record) != self._action_regime(previous):
            return True
        similarity = _jaccard(previous.context_tokens, record.context_tokens)
        if similarity < 0.20:
            return True
        previous_action = previous.action_token
        current_action = record.action_token
        if previous_action is not None and current_action is not None and previous_action != current_action:
            return True
        return False

    def observe(self, record: ExperienceRecord) -> str | None:
        """Observe one causal record and optionally close the prior episode.

        Returns the finalized episode id when this observation creates a
        temporal boundary, otherwise None. Non-observed/model records are
        ignored so replay/model output cannot self-confirm.
        """
        if not isinstance(record, ExperienceRecord):
            raise EpisodicMemoryError("record must be an ExperienceRecord")
        if record.organism_id != self._organism_id:
            raise EpisodicMemoryError("experience belongs to a different organism")
        if not _is_causal_observation(record):
            return None

        finalized: str | None = None
        if self._boundary_before(record):
            episode = self._finalize_pending()
            finalized = episode.episode_id if episode is not None else None
        self._pending.append(record)
        self._pending_payload_bytes += self._record_size(record) + 1

        # Action-outcome transitions are already natural event boundaries.
        # Keeping at most a short contiguous run prevents one long motor regime
        # from becoming a single uninformative lifetime episode. Resource
        # pressure is also a legitimate generic boundary.
        if (
            len(self._pending) >= self._limits.max_episodic_episode_records
            or self._estimated_persisted_size()
            > self._limits.max_episodic_checkpoint_bytes
        ):
            episode = self._finalize_pending()
            finalized = episode.episode_id if episode is not None else finalized
        return finalized

    def flush(self) -> str | None:
        episode = self._finalize_pending()
        return episode.episode_id if episode is not None else None

    def _episode_similarity(self, episode: ExperienceEpisode, context: Sequence[str]) -> float:
        direct = _jaccard(episode.initial_context, context)
        terminal = _jaccard(episode.terminal_context, context)
        interpretation_bonus = 0.0
        requested = set(context)
        if requested and self._interpretations.get(episode.episode_id):
            overlap = requested & self._interpretations[episode.episode_id]
            interpretation_bonus = min(0.15, 0.05 * len(overlap))
        return min(1.0, 0.80 * direct + 0.20 * terminal + interpretation_bonus)

    def _novelty_for(self, context: Sequence[str]) -> float:
        if not self._episodes:
            return 1.0
        best = max(self._episode_similarity(episode, context) for episode in self._episodes)
        return max(0.0, min(1.0, 1.0 - best))

    def _surprise_for(self, records: Sequence[ExperienceRecord]) -> float:
        outcomes = _bounded_tokens(
            token for record in records for token in record.outcome_tokens,
            limit=128,
        )
        if not outcomes or not self._episodes:
            return 0.0
        same_outcome = sum(
            1
            for episode in self._episodes
            if _jaccard(episode.outcome_tokens, outcomes) >= 0.5
        )
        frequency = same_outcome / max(1, len(self._episodes))
        return max(0.0, min(1.0, 1.0 - frequency))

    def _finalize_pending(self) -> ExperienceEpisode | None:
        if not self._pending:
            return None
        records = tuple(self._pending)
        self._pending.clear()
        self._pending_payload_bytes = 0
        initial = _bounded_tokens(records[0].context_tokens)
        terminal = _bounded_tokens(
            (*records[-1].context_tokens, *records[-1].outcome_tokens),
            limit=256,
        )
        actions = _bounded_tokens(
            (record.action_token for record in records if record.action_token is not None),
            limit=64,
        )
        outcomes = _bounded_tokens(
            (token for record in records for token in record.outcome_tokens),
            limit=128,
        )
        evidence = _bounded_tokens(
            (ref for record in records for ref in record.evidence_refs),
            limit=64,
        )
        source_ids = _bounded_tokens((record.record_id for record in records), limit=64)
        material = (
            f"{self._organism_id}|{records[0].tick_class}|{records[-1].tick_class}|"
            f"{source_ids}|{actions}|{outcomes}"
        )
        episode_id = "episode." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
        trace = tuple(
            EpisodeStep(
                tick_offset=max(0, record.tick_class - records[0].tick_class),
                source_record_id=record.record_id,
                context_tokens=record.context_tokens,
                action_token=record.action_token,
                outcome_tokens=record.outcome_tokens,
                evidence_refs=record.evidence_refs,
                confidence_class=record.confidence_class,
                source_kind=record.source_kind,
            )
            for record in records
        )
        episode = ExperienceEpisode(
            episode_id=episode_id,
            start_tick=records[0].tick_class,
            end_tick=records[-1].tick_class,
            occurrence_ticks=(records[0].tick_class,),
            trace=trace,
            initial_context=initial,
            terminal_context=terminal,
            action_tokens=actions,
            outcome_tokens=outcomes,
            evidence_refs=evidence,
            source_record_ids=source_ids,
            novelty=self._novelty_for(initial),
            surprise=self._surprise_for(records),
        )
        self._episodes.append(episode)
        self._episode_payload_bytes[episode.episode_id] = self._episode_size(episode)
        self._enforce_capacity()
        self.consolidate()
        return episode

    @staticmethod
    def _episode_signature(episode: ExperienceEpisode) -> tuple[str | None, tuple[str, ...]]:
        action = episode.action_tokens[0] if len(episode.action_tokens) == 1 else (
            "|".join(episode.action_tokens) if episode.action_tokens else None
        )
        return action, tuple(sorted(episode.outcome_tokens))

    def _merge_pair(self, left_index: int, right_index: int) -> None:
        left = self._episodes[left_index]
        right = self._episodes[right_index]
        shared_initial = tuple(sorted(set(left.initial_context) & set(right.initial_context)))
        initial = shared_initial or _bounded_tokens((*left.initial_context, *right.initial_context), limit=256)
        terminal = _bounded_tokens((*left.terminal_context, *right.terminal_context), limit=256)
        actions = _bounded_tokens((*left.action_tokens, *right.action_tokens), limit=64)
        outcomes = _bounded_tokens((*left.outcome_tokens, *right.outcome_tokens), limit=128)
        evidence = _bounded_tokens((*left.evidence_refs, *right.evidence_refs), limit=64)
        sources = _bounded_tokens((*left.source_record_ids, *right.source_record_ids), limit=64)
        material = f"compressed|{left.episode_id}|{right.episode_id}|{sources}"
        representative = max(
            (left, right),
            key=lambda episode: (
                episode.novelty + episode.surprise,
                episode.end_tick,
                episode.episode_id,
            ),
        )
        all_occurrences = sorted(set((*left.occurrence_ticks, *right.occurrence_ticks)))
        if len(all_occurrences) > 64:
            occurrence_ticks = tuple((*all_occurrences[:32], *all_occurrences[-32:]))
        else:
            occurrence_ticks = tuple(all_occurrences)
        merged_start_tick = min(left.start_tick, right.start_tick)
        representative_trace = tuple(
            EpisodeStep(
                tick_offset=(
                    representative.start_tick
                    + step.tick_offset
                    - merged_start_tick
                ),
                source_record_id=step.source_record_id,
                context_tokens=step.context_tokens,
                action_token=step.action_token,
                outcome_tokens=step.outcome_tokens,
                evidence_refs=step.evidence_refs,
                confidence_class=step.confidence_class,
                source_kind=step.source_kind,
            )
            for step in representative.trace
        )
        merged = ExperienceEpisode(
            episode_id="episode." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32],
            start_tick=merged_start_tick,
            end_tick=max(left.end_tick, right.end_tick),
            occurrence_ticks=occurrence_ticks,
            trace=representative_trace,
            initial_context=initial,
            terminal_context=terminal,
            action_tokens=actions,
            outcome_tokens=outcomes,
            evidence_refs=evidence,
            source_record_ids=sources,
            novelty=max(left.novelty, right.novelty),
            surprise=max(left.surprise, right.surprise),
            recurrence=left.recurrence + right.recurrence,
            compressed=True,
        )
        interpretations = set(
            sorted(
                self._interpretations.pop(left.episode_id, set())
                | self._interpretations.pop(right.episode_id, set())
            )[: self._limits.max_episodic_interpretations_per_episode]
        )
        retrievals = self._retrieval_counts.pop(left.episode_id, 0) + self._retrieval_counts.pop(right.episode_id, 0)
        self._episode_payload_bytes.pop(left.episode_id, None)
        self._episode_payload_bytes.pop(right.episode_id, None)
        for index in sorted((left_index, right_index), reverse=True):
            self._episodes.pop(index)
        self._episodes.append(merged)
        self._episode_payload_bytes[merged.episode_id] = self._episode_size(merged)
        if interpretations:
            self._interpretations[merged.episode_id] = interpretations
        if retrievals:
            self._retrieval_counts[merged.episode_id] = retrievals
        self._compaction_count += 1

    def _least_informative_index(self) -> int:
        if not self._episodes:
            raise EpisodicMemoryError("cannot evict from empty episodic memory")
        newest_tick = max(episode.end_tick for episode in self._episodes)

        def score(item: tuple[int, ExperienceEpisode]) -> tuple[float, int, str]:
            index, episode = item
            age = max(0, newest_tick - episode.end_tick)
            retrieval = self._retrieval_counts.get(episode.episode_id, 0)
            exception_value = 0.45 * episode.novelty + 0.45 * episode.surprise
            recurrence_value = min(1.0, episode.recurrence / 8.0)
            retrieval_value = min(1.0, retrieval / 8.0)
            keep_value = exception_value + 0.20 * recurrence_value + 0.20 * retrieval_value
            # Lower keep_value, then older age, is the preferred victim.
            return (keep_value, -age, episode.episode_id)

        return min(enumerate(self._episodes), key=score)[0]

    def _checkpoint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self._organism_id,
            "episodes": [episode.checkpoint() for episode in self._episodes],
            "pending": [record.canonical_payload() for record in self._pending],
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

    def _enforce_capacity(self) -> None:
        maximum = self._limits.max_episodic_episodes
        while (
            len(self._episodes) > maximum
            or self._estimated_persisted_size()
            > self._limits.max_episodic_checkpoint_bytes
        ):
            if not self._episodes:
                raise EpisodicMemoryError(
                    "pending episodic state alone exceeds kernel byte limit"
                )
            exact_index: dict[
                tuple[
                    tuple[str | None, tuple[str, ...]],
                    tuple[str, ...],
                ],
                int,
            ] = {}
            compact_pair: tuple[int, int] | None = None
            for index, episode in enumerate(self._episodes):
                key = (
                    self._episode_signature(episode),
                    tuple(sorted(episode.initial_context)),
                )
                previous = exact_index.get(key)
                if previous is not None:
                    compact_pair = (previous, index)
                    break
                exact_index[key] = index
            if compact_pair is not None:
                self._merge_pair(*compact_pair)
                continue
            victim = self._least_informative_index()
            episode = self._episodes.pop(victim)
            self._episode_payload_bytes.pop(episode.episode_id, None)
            self._interpretations.pop(episode.episode_id, None)
            self._retrieval_counts.pop(episode.episode_id, None)
            self._eviction_count += 1

    def replay_records(self, *, max_records: int = 8192) -> tuple[ExperienceRecord, ...]:
        """Return durable lived records for private cognitive retraining.

        These are reconstructed only from factual episode traces. Compressed
        episodes contribute their representative trace once; recurrence is not
        expanded into duplicate training samples.
        """
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
            or max_records > 65536
        ):
            raise EpisodicMemoryError("max_records must be within [1, 65536]")
        records: dict[str, ExperienceRecord] = {}
        for episode in sorted(
            self._episodes,
            key=lambda item: (item.start_tick, item.episode_id),
        ):
            for step in episode.trace:
                record = step.to_experience_record(
                    organism_id=self._organism_id,
                    episode_start_tick=episode.start_tick,
                )
                records.setdefault(record.record_id, record)
        ordered = sorted(
            records.values(),
            key=lambda item: (item.tick_class, item.record_id),
        )
        return tuple(ordered[-max_records:])

    def retrieve(
        self,
        context_tokens: Sequence[str],
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[EpisodeMatch, ...]:
        context = _bounded_tokens(context_tokens)
        limit = self._limits.max_episodic_retrieval_candidates if k is None else int(k)
        if limit < 1 or limit > self._limits.max_episodic_retrieval_candidates:
            raise EpisodicMemoryError("retrieval k exceeds kernel limit")

        ranked: list[EpisodeMatch] = []
        for episode in self._episodes:
            if action_token is not None and action_token not in episode.action_tokens:
                continue
            similarity = self._episode_similarity(episode, context)
            if similarity <= 0.0:
                continue
            ranked.append(
                EpisodeMatch(
                    episode_id=episode.episode_id,
                    similarity=similarity,
                    episode=episode,
                    interpretations=self.interpretations_for(episode.episode_id),
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.similarity,
                -item.episode.surprise,
                -item.episode.novelty,
                -item.episode.end_tick,
                item.episode_id,
            )
        )
        selected = tuple(ranked[:limit])
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
        """Associate a new representation with old episodes without rewriting them."""
        if (
            not isinstance(representation_id, str)
            or not representation_id
            or len(representation_id) > 128
        ):
            raise EpisodicMemoryError("representation_id must be a bounded non-empty string")
        if not math.isfinite(min_overlap) or not 0.0 < min_overlap <= 1.0:
            raise EpisodicMemoryError("min_overlap must be within (0, 1]")
        support = set(_bounded_tokens(support_tokens))
        if not support:
            return 0
        changed = 0
        for episode in self._episodes:
            factual = (
                set(episode.initial_context)
                | set(episode.terminal_context)
                | set(episode.action_tokens)
                | set(episode.outcome_tokens)
            )
            indexed = factual | self._interpretations.get(episode.episode_id, set())
            overlap = len(indexed & support) / len(support)
            if overlap < min_overlap:
                continue
            bucket = self._interpretations.setdefault(episode.episode_id, set())
            if representation_id in bucket:
                continue
            if (
                len(bucket)
                >= self._limits.max_episodic_interpretations_per_episode
            ):
                continue
            bucket.add(representation_id)
            if (
                self._estimated_persisted_size()
                > self._limits.max_episodic_checkpoint_bytes
            ):
                bucket.remove(representation_id)
                if not bucket:
                    self._interpretations.pop(episode.episode_id, None)
                continue
            changed += 1
        return changed

    def consolidate(self) -> tuple[ConsolidatedContingency, ...]:
        """Derive state-conditioned contingencies from independent temporal epochs."""
        groups: dict[tuple[str | None, tuple[str, ...]], list[ExperienceEpisode]] = {}
        for episode in self._episodes:
            action, outcomes = self._episode_signature(episode)
            if not outcomes:
                continue
            groups.setdefault((action, outcomes), []).append(episode)

        consolidated: dict[str, ConsolidatedContingency] = {}
        for (action, outcomes), episodes in groups.items():
            epochs = {
                tick // self._limits.episodic_epoch_ticks
                for episode in episodes
                for tick in episode.occurrence_ticks
            }
            if len(epochs) < self._limits.episodic_min_consolidation_epochs:
                continue
            token_counts = Counter(
                token for episode in episodes for token in set(episode.initial_context)
            )
            threshold = max(2, math.ceil(0.60 * len(episodes)))
            context = tuple(sorted(token for token, count in token_counts.items() if count >= threshold))
            if not context:
                # Preserve a bounded prototype rather than inventing semantics.
                context = tuple(
                    token
                    for token, _count in token_counts.most_common(16)
                )
            support_ids = tuple(sorted(episode.episode_id for episode in episodes))
            material = f"{action}|{outcomes}"
            contingency_id = "contingency." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
            confidence = min(
                1.0,
                0.5 * min(1.0, len(epochs) / 6.0)
                + 0.5 * min(1.0, sum(ep.recurrence for ep in episodes) / 8.0),
            )
            consolidated[contingency_id] = ConsolidatedContingency(
                contingency_id=contingency_id,
                context_tokens=_bounded_tokens(context, limit=64),
                action_token=action,
                outcome_tokens=_bounded_tokens(outcomes, limit=64),
                support_episode_ids=support_ids[:64],
                support_epochs=len(epochs),
                confidence=confidence,
            )
        self._consolidated = consolidated
        return self.consolidated

    def predict(
        self,
        context_tokens: Sequence[str],
        *,
        action_token: str | None,
        k: int | None = None,
    ) -> EpisodicPrediction | None:
        """Predict outcomes from similar lived episodes; never selects an action."""
        matches = self.retrieve(context_tokens, action_token=action_token, k=k)
        if not matches:
            return None
        votes: Counter[str] = Counter()
        total_weight = 0.0
        support_ids: list[str] = []
        for match in matches:
            weight = max(1e-9, match.similarity) * max(1, match.episode.recurrence)
            total_weight += weight
            support_ids.append(match.episode_id)
            for outcome in match.episode.outcome_tokens:
                votes[outcome] += weight
        if not votes or total_weight <= 0.0:
            return None
        ordered = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
        best_weight = ordered[0][1]
        predicted = tuple(token for token, weight in ordered if weight >= 0.5 * best_weight)[:16]
        confidence = min(1.0, best_weight / total_weight)
        return EpisodicPrediction(
            action_token=action_token,
            predicted_outcomes=predicted,
            confidence=confidence,
            support_episode_ids=tuple(support_ids),
        )

    def cognitive_replay(
        self,
        context_tokens: Sequence[str],
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[CognitiveReplay, ...]:
        """Reactivate compact episode representations without motor execution."""
        limit = self._limits.max_episodic_replay_items if k is None else int(k)
        if limit < 1 or limit > self._limits.max_episodic_replay_items:
            raise EpisodicMemoryError("replay k exceeds kernel limit")
        matches = self.retrieve(context_tokens, action_token=action_token, k=limit)
        result = tuple(
            CognitiveReplay(
                episode_id=match.episode_id,
                similarity=match.similarity,
                trace=match.episode.trace,
                context_tokens=match.episode.initial_context,
                action_tokens=match.episode.action_tokens,
                outcome_tokens=match.episode.outcome_tokens,
                interpretations=match.interpretations,
            )
            for match in matches
        )
        if result:
            self._replay_count += 1
        return result

    def metrics(self, *, current_tick: int) -> EpisodicMemoryMetrics:
        ages = [max(0, current_tick - episode.end_tick) for episode in self._episodes]
        return EpisodicMemoryMetrics(
            episode_count=len(self._episodes),
            pending_records=len(self._pending),
            compressed_episode_count=sum(episode.compressed for episode in self._episodes),
            interpretation_count=sum(len(values) for values in self._interpretations.values()),
            consolidated_contingencies=len(self._consolidated),
            retrieval_count=self._retrieval_count,
            replay_count=self._replay_count,
            compaction_count=self._compaction_count,
            eviction_count=self._eviction_count,
            oldest_episode_age=max(ages, default=0),
            mean_episode_age=(sum(ages) / len(ages) if ages else 0.0),
        )

    def checkpoint(self) -> dict[str, object]:
        payload = self._checkpoint_payload()
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self._limits.max_episodic_checkpoint_bytes:
            # Pending state is intentionally not discarded merely because a
            # save was requested. If the live invariant cannot hold, fail
            # visibly rather than silently changing lived history.
            raise EpisodicMemoryError("episodic checkpoint exceeds kernel byte limit")
        return payload

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
        *,
        organism_id: str,
        kernel_limits: KernelLimits | None = None,
    ) -> "EpisodicExperienceMemory":
        memory = cls(organism_id, kernel_limits=kernel_limits)
        if payload is None:
            return memory
        if not isinstance(payload, Mapping) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise EpisodicMemoryError("invalid episodic memory checkpoint")
        if payload.get("organism_id") != organism_id:
            raise EpisodicMemoryError("episodic memory organism mismatch")
        if memory._json_size(payload) > memory._limits.max_episodic_checkpoint_bytes:
            raise EpisodicMemoryError("episodic checkpoint exceeds kernel byte limit")

        raw_episodes = payload.get("episodes", [])
        if (
            not isinstance(raw_episodes, list)
            or len(raw_episodes) > memory._limits.max_episodic_episodes
        ):
            raise EpisodicMemoryError("invalid episodic episode collection")
        for item in raw_episodes:
            if not isinstance(item, Mapping):
                continue
            raw_trace = item.get("trace")
            if (
                not isinstance(raw_trace, list)
                or len(raw_trace) > memory._limits.max_episodic_episode_records
            ):
                raise EpisodicMemoryError(
                    "episode trace exceeds configured kernel limit"
                )
        memory._episodes = [
            ExperienceEpisode.restore(item)
            for item in raw_episodes
            if isinstance(item, Mapping)
        ]
        if len(memory._episodes) != len(raw_episodes):
            raise EpisodicMemoryError("episodic episode must be an object")
        episode_ids_in_order = [episode.episode_id for episode in memory._episodes]
        if len(set(episode_ids_in_order)) != len(episode_ids_in_order):
            raise EpisodicMemoryError("duplicate episodic episode_id")
        memory._episode_payload_bytes = {
            episode.episode_id: memory._episode_size(episode)
            for episode in memory._episodes
        }

        raw_pending = payload.get("pending", [])
        if (
            not isinstance(raw_pending, list)
            or len(raw_pending) > memory._limits.max_episodic_episode_records
        ):
            raise EpisodicMemoryError("invalid pending episodic records")
        for raw in raw_pending:
            if not isinstance(raw, dict):
                raise EpisodicMemoryError("pending episodic record must be an object")
            record = ExperienceRecord.restore(raw)
            if record.organism_id != organism_id or not _is_causal_observation(record):
                raise EpisodicMemoryError("invalid pending causal record")
            memory._pending.append(record)
            memory._pending_payload_bytes += memory._record_size(record) + 1

        episode_ids = {episode.episode_id for episode in memory._episodes}
        raw_interpretations = payload.get("interpretations", {})
        if not isinstance(raw_interpretations, Mapping):
            raise EpisodicMemoryError("invalid episodic interpretations")
        for episode_id, raw_values in raw_interpretations.items():
            if episode_id not in episode_ids:
                raise EpisodicMemoryError("interpretation references unknown episode")
            if (
                not isinstance(raw_values, list)
                or len(raw_values)
                > memory._limits.max_episodic_interpretations_per_episode
                or any(not isinstance(value, str) or not value for value in raw_values)
            ):
                raise EpisodicMemoryError("invalid episodic interpretation values")
            memory._interpretations[str(episode_id)] = set(raw_values)

        raw_retrieval = payload.get("retrieval_counts", {})
        if not isinstance(raw_retrieval, Mapping):
            raise EpisodicMemoryError("invalid episodic retrieval counts")
        for episode_id, count in raw_retrieval.items():
            if episode_id not in episode_ids:
                continue
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise EpisodicMemoryError("invalid episodic retrieval count")
            memory._retrieval_counts[str(episode_id)] = count

        raw_metrics = payload.get("metrics", {})
        if not isinstance(raw_metrics, Mapping):
            raise EpisodicMemoryError("invalid episodic metrics")
        for name in ("retrieval_count", "replay_count", "compaction_count", "eviction_count"):
            value = raw_metrics.get(name, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise EpisodicMemoryError(f"invalid episodic metric {name}")
            setattr(memory, f"_{name}", value)

        if (
            memory._estimated_persisted_size()
            > memory._limits.max_episodic_checkpoint_bytes
        ):
            raise EpisodicMemoryError("episodic checkpoint exceeds kernel byte limit")
        memory.consolidate()
        return memory


__all__ = [
    "CognitiveReplay",
    "ConsolidatedContingency",
    "EpisodeMatch",
    "EpisodicExperienceMemory",
    "EpisodicMemoryError",
    "EpisodicMemoryMetrics",
    "EpisodicPrediction",
    "EpisodeStep",
    "ExperienceEpisode",
]
