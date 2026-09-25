"""Endogenous agenda for bounded generative processing.

The agenda stores opaque organism-owned unresolved structures.  It never accepts
laboratory labels, evaluator results, or hidden world state as target input.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .types import bounded_identifier, bounded_tuple, unit_interval


class AgendaContaminationError(ValueError):
    """Raised when an external task or evaluator attempts to create a target."""


class AgendaSource(str, Enum):
    PREDICTION_ERROR = "prediction_error"
    MODEL_DISAGREEMENT = "model_disagreement"
    ACTIVE_HYPOTHESIS = "active_hypothesis"
    UNCERTAINTY = "uncertainty"
    EPISODIC_INCOMPLETENESS = "episodic_incompleteness"
    PROSPECTIVE_DECISION = "prospective_decision"
    RECURRING_CONFLICT = "recurring_conflict"


class TargetStatus(str, Enum):
    ELIGIBLE = "eligible"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class GenerativeTarget:
    target_id: str
    source: AgendaSource
    source_refs: tuple[str, ...]
    created_tick: int
    uncertainty: float
    persistence: float
    recurrence: int
    estimated_resolvability: float | None = None
    last_selected_tick: int | None = None
    selection_count: int = 0
    last_progress_tick: int | None = None
    status: TargetStatus = TargetStatus.ELIGIBLE
    no_progress_count: int = 0
    suppressed_until: int | None = None

    def __post_init__(self) -> None:
        bounded_identifier(self.target_id, name="target_id")
        if not isinstance(self.source, AgendaSource):
            raise ValueError("source must be an AgendaSource")
        bounded_tuple(self.source_refs, name="source_refs")
        if not self.source_refs:
            raise ValueError("agenda target requires organism-owned source_refs")
        if (
            isinstance(self.created_tick, bool)
            or not isinstance(self.created_tick, int)
            or self.created_tick < 0
        ):
            raise ValueError("created_tick must be a non-negative integer")
        unit_interval(self.uncertainty, name="uncertainty")
        unit_interval(self.persistence, name="persistence")
        if self.estimated_resolvability is not None:
            unit_interval(self.estimated_resolvability, name="estimated_resolvability")
        for name, value in (
            ("recurrence", self.recurrence),
            ("selection_count", self.selection_count),
            ("no_progress_count", self.no_progress_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name, value in (
            ("last_selected_tick", self.last_selected_tick),
            ("last_progress_tick", self.last_progress_tick),
            ("suppressed_until", self.suppressed_until),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer or None")
        if not isinstance(self.status, TargetStatus):
            raise ValueError("status must be a TargetStatus")


@dataclass(frozen=True, slots=True)
class AgendaCandidate:
    target: GenerativeTarget
    uncertainty_signal: float
    recurrence_signal: float
    conflict_signal: float
    expected_information_gain: float | None
    estimated_resolvability: float | None
    recent_attention: float
    progress_signal: float | None

    @property
    def priority(self) -> float:
        # Technical scheduling score only; it is not a reward or world truth.
        return (
            0.30 * self.uncertainty_signal
            + 0.20 * self.recurrence_signal
            + 0.20 * self.conflict_signal
            + 0.15 * (self.expected_information_gain or 0.0)
            + 0.10 * (self.estimated_resolvability or 0.0)
            + 0.05 * max(0.0, 1.0 - self.recent_attention)
        )


@dataclass(frozen=True, slots=True)
class AgendaProgress:
    new_branch: bool = False
    uncertainty_changed: bool = False
    disagreement_changed: bool = False
    hypothesis_changed: bool = False
    discriminating_consequence: bool = False
    reconciliation: bool = False

    @property
    def made_progress(self) -> bool:
        return any(
            (
                self.new_branch,
                self.uncertainty_changed,
                self.disagreement_changed,
                self.hypothesis_changed,
                self.discriminating_consequence,
                self.reconciliation,
            )
        )


class GenerativeAgenda:
    """Bounded, deterministic target selection with anti-rumination state."""

    def __init__(
        self,
        *,
        max_targets: int = 64,
        max_reselection_without_progress: int = 3,
        suppression_duration: int = 8,
    ) -> None:
        if max_targets < 0 or max_reselection_without_progress < 0 or suppression_duration < 0:
            raise ValueError("agenda limits must be non-negative")
        self.max_targets = max_targets
        self.max_reselection_without_progress = max_reselection_without_progress
        self.suppression_duration = suppression_duration
        self._targets: dict[str, GenerativeTarget] = {}
        self.agenda_contamination_count = 0

    @property
    def targets(self) -> tuple[GenerativeTarget, ...]:
        return tuple(self._targets.values())

    def add_target(self, target: GenerativeTarget) -> None:
        if not isinstance(target, GenerativeTarget):
            raise ValueError("agenda accepts only GenerativeTarget values")
        if target.target_id in self._targets:
            raise ValueError("duplicate agenda target")
        if len(self._targets) >= self.max_targets:
            raise ValueError("maximum agenda targets reached")
        self._targets[target.target_id] = target

    def reject_external_target(self, value: object) -> None:
        self.agenda_contamination_count += 1
        raise AgendaContaminationError(
            "external task, evaluator, or hidden world state cannot enter agenda"
        )

    def select(self, *, tick: int, limit: int = 1) -> tuple[AgendaCandidate, ...]:
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0 or limit < 0:
            raise ValueError("tick and limit must be non-negative integers")
        candidates = [
            self._candidate(target, tick)
            for target in self._targets.values()
            if self._eligible(target, tick)
        ]
        candidates.sort(key=lambda item: (-item.priority, item.target.target_id))
        selected = candidates[:limit]
        for candidate in selected:
            target = candidate.target
            self._targets[target.target_id] = replace(
                target, last_selected_tick=tick, selection_count=target.selection_count + 1
            )
        return tuple(selected)

    def record_progress(self, target_id: str, *, tick: int, progress: AgendaProgress) -> None:
        target = self._get(target_id)
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if not isinstance(progress, AgendaProgress):
            raise ValueError("progress must be AgendaProgress")
        if progress.made_progress:
            self._targets[target_id] = replace(
                target,
                last_progress_tick=tick,
                no_progress_count=0,
                status=TargetStatus.ELIGIBLE,
                suppressed_until=None,
            )
            return
        failures = target.no_progress_count + 1
        if failures >= self.max_reselection_without_progress:
            self._targets[target_id] = replace(
                target,
                no_progress_count=failures,
                status=TargetStatus.SUPPRESSED,
                suppressed_until=tick + self.suppression_duration,
            )
        else:
            self._targets[target_id] = replace(target, no_progress_count=failures)

    def resolve(self, target_id: str) -> None:
        self._set_status(target_id, TargetStatus.RESOLVED)

    def retire(self, target_id: str) -> None:
        self._set_status(target_id, TargetStatus.RETIRED)

    def _get(self, target_id: str) -> GenerativeTarget:
        bounded_identifier(target_id, name="target_id")
        try:
            return self._targets[target_id]
        except KeyError as exc:
            raise KeyError(f"unknown agenda target: {target_id}") from exc

    def _set_status(self, target_id: str, status: TargetStatus) -> None:
        self._targets[target_id] = replace(
            self._get(target_id), status=status, suppressed_until=None
        )

    @staticmethod
    def _eligible(target: GenerativeTarget, tick: int) -> bool:
        return target.status is TargetStatus.ELIGIBLE or (
            target.status is TargetStatus.SUPPRESSED
            and target.suppressed_until is not None
            and tick >= target.suppressed_until
        )

    @staticmethod
    def _candidate(target: GenerativeTarget, tick: int) -> AgendaCandidate:
        attention = (
            0.0
            if target.last_selected_tick is None
            else 1.0 / (1.0 + tick - target.last_selected_tick)
        )
        return AgendaCandidate(
            target=target,
            uncertainty_signal=target.uncertainty,
            recurrence_signal=min(1.0, target.recurrence / 8.0),
            conflict_signal=1.0
            if target.source in {AgendaSource.MODEL_DISAGREEMENT, AgendaSource.RECURRING_CONFLICT}
            else 0.0,
            expected_information_gain=target.estimated_resolvability,
            estimated_resolvability=target.estimated_resolvability,
            recent_attention=attention,
            progress_signal=None,
        )


__all__ = [
    "AgendaCandidate",
    "AgendaContaminationError",
    "AgendaProgress",
    "AgendaSource",
    "GenerativeAgenda",
    "GenerativeTarget",
    "TargetStatus",
]
