"""Durable but non-authoritative generative hypotheses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .types import bounded_identifier, bounded_tuple, unit_interval


class HypothesisStatus(str, Enum):
    HYPOTHESIZED = "hypothesized"
    PREDICTED = "predicted"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    RETIRED = "retired"


@dataclass(slots=True)
class GenerativeHypothesis:
    hypothesis_id: str
    source_episode_ids: tuple[str, ...]
    source_model_ids: tuple[str, ...]
    uncertainty: float
    status: HypothesisStatus = HypothesisStatus.HYPOTHESIZED
    factual_support_refs: tuple[str, ...] = ()
    factual_conflict_refs: tuple[str, ...] = ()
    _reconciliation_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        bounded_identifier(self.hypothesis_id, name="hypothesis_id")
        bounded_tuple(self.source_episode_ids, name="source_episode_ids")
        bounded_tuple(self.source_model_ids, name="source_model_ids")
        bounded_tuple(self.factual_support_refs, name="factual_support_refs")
        bounded_tuple(self.factual_conflict_refs, name="factual_conflict_refs")
        unit_interval(self.uncertainty, name="uncertainty")
        if not isinstance(self.status, HypothesisStatus):
            raise ValueError("status must be a HypothesisStatus")

    def mark_predicted(self) -> None:
        if self.status not in {HypothesisStatus.HYPOTHESIZED, HypothesisStatus.PREDICTED}:
            raise ValueError("only active hypotheses can become predicted")
        self.status = HypothesisStatus.PREDICTED

    def retire(self) -> None:
        self.status = HypothesisStatus.RETIRED

    def _reconcile(self, *, evidence_ref: str, supported: bool) -> None:
        bounded_identifier(evidence_ref, name="evidence_ref")
        if self.status not in {HypothesisStatus.HYPOTHESIZED, HypothesisStatus.PREDICTED}:
            raise ValueError("only active hypotheses can be reconciled")
        if supported:
            self.factual_support_refs = _append_unique(self.factual_support_refs, evidence_ref)
            self.status = HypothesisStatus.SUPPORTED
        else:
            self.factual_conflict_refs = _append_unique(self.factual_conflict_refs, evidence_ref)
            self.status = HypothesisStatus.CONTRADICTED
        self._reconciliation_count += 1


def _append_unique(values: tuple[str, ...], value: str) -> tuple[str, ...]:
    return values if value in values else (*values, value)


__all__ = ["GenerativeHypothesis", "HypothesisStatus"]
