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
    predictive_context_count: int
    agency_estimate_count: int
    composition_evidence_count: int
    established_composition_count: int
    body_schema_sensorimotor_relations: int
    active_commitment_id: str | None
    active_competence_id: str | None
    action_source: str
    exploration_preference: tuple[str, ...]
    mean_learning_progress: float
    # Agency Acquisition & Executive Action v1 §90.
    physical_motor_opportunity_count: int = 0
    action_attempt_count: int = 0
    intervention_signature_count: int = 0
    recurring_intervention_signature_count: int = 0
    action_dimension_count: int = 0
    agentic_action_dimension_count: int = 0
    affordance_count: int = 0
    active_intent_id: str | None = None
    active_intent_status: str | None = None
    active_intent_age: int | None = None
    active_intent_last_progress_age: int | None = None
    intent_satisfied_count: int = 0
    intent_failed_count: int = 0
    intent_rejected_count: int = 0
    intent_interrupted_count: int = 0
    intent_invalidated_count: int = 0
    intent_prediction_match: float | None = None

    def __post_init__(self) -> None:
        counts = (
            self.effect_count,
            self.causal_evidence_count,
            self.competence_count,
            self.established_competence_count,
            self.competence_candidate_count,
            self.controllability_estimate_count,
            self.predictive_context_count,
            self.agency_estimate_count,
            self.composition_evidence_count,
            self.established_composition_count,
            self.body_schema_sensorimotor_relations,
            self.physical_motor_opportunity_count,
            self.action_attempt_count,
            self.intervention_signature_count,
            self.recurring_intervention_signature_count,
            self.action_dimension_count,
            self.agentic_action_dimension_count,
            self.affordance_count,
            self.intent_satisfied_count,
            self.intent_failed_count,
            self.intent_rejected_count,
            self.intent_interrupted_count,
            self.intent_invalidated_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("sensorimotor snapshot counts must be non-negative")
        if self.mean_learning_progress < 0.0:
            raise ValueError("mean_learning_progress must be non-negative")
