"""Passive public state for Sensorimotor v2."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SensorimotorV2Snapshot:
    effect_count: int
    causal_evidence_count: int
    competence_count: int
    established_competence_count: int
    competence_candidate_count: int
    controllability_estimate_count: int
    composition_evidence_count: int
    established_composition_count: int
    body_schema_sensorimotor_relations: int
    active_commitment_id: str | None
    active_competence_id: str | None
    action_source: str
    exploration_preference: tuple[str, ...]
    mean_learning_progress: float

    def __post_init__(self) -> None:
        counts = (
            self.effect_count,
            self.causal_evidence_count,
            self.competence_count,
            self.established_competence_count,
            self.competence_candidate_count,
            self.controllability_estimate_count,
            self.composition_evidence_count,
            self.established_composition_count,
            self.body_schema_sensorimotor_relations,
        )
        if any(value < 0 for value in counts):
            raise ValueError("sensorimotor snapshot counts must be non-negative")
        if self.mean_learning_progress < 0.0:
            raise ValueError("mean_learning_progress must be non-negative")
