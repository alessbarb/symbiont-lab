"""IntentionDomain: owner of the persistent cognitive commitment to a consequence.

It forms, activates, rejects, reconciles and terminates ActionIntents.  It
never arbitrates, never issues commands, never selects actuators and never
runs controllers (§46).  Motor authority stays with the ActionArbitrator and
the ActionCommitment it grants; physical execution stays with ActionDomain.
"""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping

from ...actuation.commitment import CommitmentStatus
from ...actuation.evidence import PredictionError
from ...agency.executive_outcome import (
    NO_HISTORY,
    CausalRevisionState,
    ExecutiveKey,
    ExecutiveModulation,
    ExecutiveOutcomeLedger,
    ExecutiveOutcomeSample,
    OutcomeClass,
    classify_outcome,
)
from ...agency.intention import ActionIntent, IntentStatus
from ...agency.prospective import ProspectiveDecision
from ...provenance import CausalEvent, CausalRef, ProvenanceLog

# Termination reasons (§60, §68-§70). Evidence-bearing, not extra states.
PROPOSAL_NOT_SELECTED = "proposal_not_selected"
SUPERSEDED_BY_PROTECTION = "superseded_by_protection"
SUPERSEDED_BY_OTHER_ACTION = "superseded_by_other_action"
ANTICIPATED_EFFECT_OBSERVED = "anticipated_effect_observed"
COMMITMENT_COMPLETED_UNVERIFIED = "commitment_completed_unverified"
CONTROLLER_TERMINAL_FAILURE = "controller_terminal_failure"
COMMITMENT_TERMINAL_FAILURE = "commitment_terminal_failure"
REPEATED_HIGH_MISMATCH = "repeated_high_mismatch"
STAGNATION = "stagnation"
COMPETENCE_EXHAUSTED = "competence_exhausted_without_anticipated_consequence"
EMBODIMENT_CHANGED = "embodiment_changed"
SURFACE_INCOMPATIBLE = "surface_incompatible"
COMPETENCE_NOT_EXECUTABLE = "competence_no_longer_executable"
CAUSAL_BINDING_INVALIDATED = "required_causal_binding_invalidated"
PROTECTION_TAKES_PRIORITY = "protection_takes_priority"
NEW_MOTOR_AUTHORITY = "new_motor_authority_supersedes_commitment"
HOMEOSTATIC_EMERGENCY = "homeostatic_emergency"
RECONSIDERED = "reconsidered_each_tick"


class ExecutiveMode(StrEnum):
    """How cognition reaches motor authority.

    FULL is the organism.  The other values exist only as explicit
    experimental control arms (E2/E3/E5) and are never selected implicitly.
    """

    FULL = "full"
    DIRECT_PROPOSAL = "direct_proposal"  # readout/competence -> proposal, no intent
    UNRECONCILED_INTENT = "unreconciled_intent"  # intents without real-effect feedback
    REDECIDE_EACH_TICK = "redecide_each_tick"  # no intent persistence


@dataclass(frozen=True)
class IntentionPolicy:
    """Experimental reconciliation parameters, not frozen scientific values."""

    satisfaction_similarity: float = 1.0
    minimum_progress_evidence: int = 1
    max_consecutive_mismatches: int = 3
    stagnation_ticks: int = 12
    # E5 condition B only: intents that are never reconciled with real effects.
    reconcile_observed_effects: bool = True
    # Executive Outcome Learning v1: real outcomes modulate future admission.
    # Disabled only as an explicit study arm (E2/E5 v3 arm C).
    executive_outcome_learning: bool = True
    # Factorized Effect Representation v1 §14.1: a footprint-anticipated
    # intent is satisfied when this fraction of its expected atoms has been
    # observed across its commitment (recall, accumulated per commitment).
    footprint_satisfaction_recall: float = 0.75

    def __post_init__(self) -> None:
        value = float(self.satisfaction_similarity)
        if not math.isfinite(value) or not 0.0 < value <= 1.0:
            raise ValueError("satisfaction_similarity must be within (0, 1]")
        recall = float(self.footprint_satisfaction_recall)
        if not math.isfinite(recall) or not 0.0 < recall <= 1.0:
            raise ValueError("footprint_satisfaction_recall must be within (0, 1]")
        if self.minimum_progress_evidence < 1 or self.max_consecutive_mismatches < 1:
            raise ValueError("evidence thresholds must be positive")
        if self.stagnation_ticks < 1:
            raise ValueError("stagnation_ticks must be positive")


@dataclass(frozen=True, slots=True)
class IntentOutcome:
    """Observable result of one intent lifecycle transition (§86)."""

    intent_id: str
    competence_id: str
    anticipated_effect_id: str | None
    status: IntentStatus
    reason: str | None
    tick: int
    commitment_id: str | None
    observed_effect_id: str | None
    effect_similarity: float | None
    context_ref: str | None = None
    progress_before_termination: float | None = None
    mean_prediction_mismatch: float | None = None
    binding_valid_at_start: bool = False


class IntentionDomain:
    """Single-slot executive intention (one PENDING or ACTIVE intent at a time)."""

    SCHEMA_VERSION = 2

    def __init__(self, *, organism_id: str, policy: IntentionPolicy | None = None) -> None:
        if not organism_id:
            raise ValueError("organism_id must not be empty")
        self.organism_id = organism_id
        self.policy = policy or IntentionPolicy()
        self.active: ActionIntent | None = None
        self.active_commitment_id: str | None = None
        self._progress_evidence = 0
        self._consecutive_mismatches = 0
        self._formed = 0
        self.counts: dict[IntentStatus, int] = {
            status: 0
            for status in (
                IntentStatus.SATISFIED,
                IntentStatus.FAILED,
                IntentStatus.REJECTED,
                IntentStatus.INTERRUPTED,
                IntentStatus.INVALIDATED,
            )
        }
        self.last_outcomes: tuple[IntentOutcome, ...] = ()
        self.recent_outcomes: deque[IntentOutcome] = deque(maxlen=32)
        self.last_prediction_match: float | None = None
        # Reconciliation trace of the live intent (EOL samples).
        self._binding_valid_at_start = False
        self._best_similarity: float | None = None
        self._mismatch_sum = 0.0
        self._mismatch_count = 0
        self.outcome_ledger = ExecutiveOutcomeLedger()
        # Supplied by the action domain: the material causal/binding state of
        # one (competence, effect) relation.  Read-only.
        self.revision_probe: Callable[[ExecutiveKey], CausalRevisionState] | None = None
        # Footprint expectation snapshot of the live intent and the atoms
        # observed across its commitment (Factorized Effects §14.1).
        self._expected_atoms: tuple[str, ...] = ()
        self._observed_atoms: set[str] = set()
        # Organism-level causal provenance, supplied by the action domain.
        self.provenance: ProvenanceLog | None = None

    # -- lifecycle ------------------------------------------------------------
    def begin_tick(self) -> None:
        self.last_outcomes = ()

    @property
    def holds_intent(self) -> bool:
        return self.active is not None and not self.active.terminal

    def form(
        self,
        decision: ProspectiveDecision,
        *,
        context_ref: str | None,
        embodiment_id: str | None,
        tick: int,
    ) -> ActionIntent:
        """ProspectiveDecision -> ActionIntent(PENDING); never re-forms a held intent."""
        held = self.active
        if held is not None and not held.terminal:
            if (
                held.competence_id == decision.competence_id
                and held.anticipated_effect_id == decision.anticipated_effect_id
            ):
                return held
            raise RuntimeError("an intent is already held; terminate it before forming another")
        self._formed += 1
        material = (
            f"{self.organism_id}|{decision.competence_id}|{decision.anticipated_effect_id}"
            f"|{tick}|{self._formed}"
        )
        intent = ActionIntent(
            intent_id="intent." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24],
            competence_id=decision.competence_id,
            anticipated_effect_id=decision.anticipated_effect_id,
            context_ref=context_ref,
            embodiment_id=embodiment_id,
            origin_refs=decision.origin_refs,
            prediction_ref=decision.prediction_ref,
            confidence=decision.confidence,
            epistemic_relevance=decision.epistemic_relevance,
            homeostatic_relevance=decision.homeostatic_relevance,
            supporting_affordance_id=decision.supporting_affordance_id,
            created_tick=int(tick),
            activated_tick=None,
            last_progress_tick=int(tick),
            status=IntentStatus.PENDING,
            termination_reason=None,
            admission=decision.admission,
        )
        self.active = intent
        self.active_commitment_id = None
        self._progress_evidence = 0
        self._consecutive_mismatches = 0
        self.last_prediction_match = None
        self._binding_valid_at_start = False
        self._best_similarity = None
        self._mismatch_sum = 0.0
        self._mismatch_count = 0
        self._expected_atoms = ()
        self._observed_atoms = set()
        self._emit(
            intent,
            tick=tick,
            operation="form",
            caused_by=(
                CausalRef("competence", intent.competence_id),
                *(
                    (CausalRef("effect", intent.anticipated_effect_id),)
                    if intent.anticipated_effect_id
                    else ()
                ),
            ),
            parameters={"admission": intent.admission.value},
        )
        return intent

    def expect_atoms(self, atoms: tuple[str, ...]) -> None:
        """Snapshot the footprint atoms the live intent is expected to produce."""
        self._expected_atoms = tuple(sorted(set(atoms)))
        self._observed_atoms = set()

    @property
    def expected_atoms(self) -> tuple[str, ...]:
        return self._expected_atoms

    def _emit(self, intent, *, tick, operation, caused_by, parameters, rule=None) -> None:
        if self.provenance is None:
            return
        ref = CausalRef("intent", intent.intent_id)
        self.provenance.emit(
            CausalEvent(
                tick=int(tick),
                domain="intention",
                operation=operation,
                subject=ref,
                caused_by=tuple(caused_by),
                produced=(ref,),
                rule=rule,
                parameters=parameters,
            )
        )

    def _held(self, intent_id: str) -> ActionIntent:
        intent = self.active
        if intent is None or intent.intent_id != intent_id:
            raise KeyError(f"intent {intent_id} is not held")
        return intent

    def activate(
        self,
        intent_id: str,
        *,
        commitment_id: str,
        tick: int,
        binding_valid: bool = False,
    ) -> ActionIntent:
        """The arbitrator granted motor authority to this intent's proposal (§59).

        ``binding_valid`` records whether the competence was executable when
        authority was granted; only then can a controller failure count as
        executive evidence against it (EOL §5).
        """
        intent = self._held(intent_id)
        intent.transition(IntentStatus.ACTIVE, tick=tick)
        self.active_commitment_id = commitment_id
        self._binding_valid_at_start = bool(binding_valid)
        return intent

    def _terminate(
        self,
        intent: ActionIntent,
        status: IntentStatus,
        *,
        reason: str,
        tick: int,
        observed_effect_id: str | None = None,
        similarity: float | None = None,
    ) -> IntentOutcome:
        intent.transition(status, tick=tick, reason=reason)
        self.counts[status] += 1
        outcome = IntentOutcome(
            intent_id=intent.intent_id,
            competence_id=intent.competence_id,
            anticipated_effect_id=intent.anticipated_effect_id,
            status=status,
            reason=reason,
            tick=int(tick),
            commitment_id=self.active_commitment_id,
            observed_effect_id=observed_effect_id,
            effect_similarity=similarity,
            context_ref=intent.context_ref,
            progress_before_termination=self._best_similarity,
            mean_prediction_mismatch=(
                self._mismatch_sum / self._mismatch_count if self._mismatch_count else None
            ),
            binding_valid_at_start=self._binding_valid_at_start,
        )
        self.last_outcomes = (*self.last_outcomes, outcome)
        self.recent_outcomes.append(outcome)
        causes = [CausalRef("intent", intent.intent_id)]
        if self.active_commitment_id is not None:
            causes.append(CausalRef("commitment", self.active_commitment_id))
        self._emit(
            intent,
            tick=tick,
            operation=status.value,
            caused_by=causes,
            rule=reason,
            parameters={
                "effect_similarity": similarity if similarity is not None else -1.0,
                "expected_atoms": len(self._expected_atoms),
                "observed_expected_atoms": len(self._observed_atoms & set(self._expected_atoms)),
            },
        )
        if self.provenance is not None:
            self.provenance.retire((CausalRef("intent", intent.intent_id),))
        self._learn_from_outcome(outcome)
        return outcome

    # -- Executive Outcome Learning v1 ---------------------------------------------
    def _learn_from_outcome(self, outcome: IntentOutcome) -> None:
        """Real outcome -> executive evidence for its key; never causal evidence."""
        if not self.policy.executive_outcome_learning or outcome.anticipated_effect_id is None:
            return
        outcome_class = classify_outcome(
            status=outcome.status.value,
            reason=outcome.reason,
            binding_valid_at_start=outcome.binding_valid_at_start,
        )
        if outcome_class is OutcomeClass.NEUTRAL:
            return
        key: ExecutiveKey = (outcome.competence_id, outcome.anticipated_effect_id)
        revision = None
        if outcome_class is OutcomeClass.SUPPRESS:
            if self.revision_probe is None:
                # Detached from an action domain there is no causal/binding
                # state to judge the invalidation against; a suppression that
                # could never lift is not recorded.  ActionDomain always
                # installs the probe.
                return
            revision = self.revision_probe(key)
        self.outcome_ledger.record(
            key,
            ExecutiveOutcomeSample(
                tick=outcome.tick,
                outcome_class=outcome_class,
                reason=outcome.reason,
                effect_similarity=outcome.effect_similarity,
                prediction_mismatch=outcome.mean_prediction_mismatch,
                progress_before_failure=(
                    outcome.progress_before_termination
                    if outcome_class is not OutcomeClass.POSITIVE
                    else None
                ),
            ),
            revision=revision,
        )

    def admission_modulation(
        self,
        *,
        competence_id: str,
        anticipated_effect_id: str,
    ) -> ExecutiveModulation:
        """How this relation's executive history modulates its admission (EOL §6-§7)."""
        if not self.policy.executive_outcome_learning:
            return NO_HISTORY
        key: ExecutiveKey = (competence_id, anticipated_effect_id)
        revision = self.revision_probe(key) if self.revision_probe is not None else None
        return self.outcome_ledger.modulation(key, revision=revision)

    def reject(self, intent_id: str, *, reason: str, tick: int) -> IntentOutcome:
        """PENDING -> REJECTED: motor authority was never granted (§41, §60)."""
        return self._terminate(
            self._held(intent_id), IntentStatus.REJECTED, reason=reason, tick=tick
        )

    def fail(self, intent_id: str, *, reason: str, tick: int) -> IntentOutcome:
        return self._terminate(self._held(intent_id), IntentStatus.FAILED, reason=reason, tick=tick)

    def interrupt(self, intent_id: str, *, reason: str, tick: int) -> IntentOutcome:
        """ACTIVE -> INTERRUPTED: execution had started and was superseded (§70)."""
        return self._terminate(
            self._held(intent_id), IntentStatus.INTERRUPTED, reason=reason, tick=tick
        )

    def invalidate(self, intent_id: str, *, reason: str, tick: int) -> IntentOutcome:
        return self._terminate(
            self._held(intent_id), IntentStatus.INVALIDATED, reason=reason, tick=tick
        )

    # -- T3 reconciliation ------------------------------------------------------
    def observe_effect(
        self,
        *,
        observed_effect_id: str | None,
        prediction_error: PredictionError | None,
        effect_similarity: float | None,
        tick: int,
        commitment_id: str | None,
        commitment_status: CommitmentStatus | None,
        competence_executable: bool,
        embodiment_id: str | None,
        observed_atoms: tuple[str, ...] = (),
    ) -> IntentOutcome | None:
        """Reconcile the ACTIVE intent with what physically happened (§64-§70).

        A footprint-anticipated intent (with an expected atom snapshot) is
        reconciled per commitment: expected atoms observed across the
        commitment accumulate and their recall is compared with
        ``footprint_satisfaction_recall`` (Factorized Effects §14.1).

        ``commitment_id`` names the commitment whose attempt produced this
        observation (None when nothing was observed for an attempt).
        ``commitment_status`` is the current status of the intent's own
        commitment after this tick's controller completion.
        """
        intent = self.active
        if intent is None or intent.status is not IntentStatus.ACTIVE:
            return None
        if intent.embodiment_id is not None and embodiment_id != intent.embodiment_id:
            return self.invalidate(intent.intent_id, reason=EMBODIMENT_CHANGED, tick=tick)
        if not competence_executable:
            return self.invalidate(intent.intent_id, reason=COMPETENCE_NOT_EXECUTABLE, tick=tick)

        own_observation = commitment_id is not None and commitment_id == self.active_commitment_id
        if own_observation and self.policy.reconcile_observed_effects:
            if prediction_error is not None:
                self.last_prediction_match = max(0.0, 1.0 - float(prediction_error.magnitude))
                self._mismatch_sum += float(prediction_error.magnitude)
                self._mismatch_count += 1
            if self._expected_atoms:
                expected = set(self._expected_atoms)
                before = len(self._observed_atoms)
                self._observed_atoms.update(atom for atom in observed_atoms if atom in expected)
                similarity = len(self._observed_atoms) / len(expected)
                threshold = self.policy.footprint_satisfaction_recall
                progressed = len(self._observed_atoms) > before
                mismatched = not self._observed_atoms and bool(observed_atoms)
            else:
                similarity = 0.0 if effect_similarity is None else float(effect_similarity)
                threshold = self.policy.satisfaction_similarity
                progressed = similarity > 0.0
                mismatched = observed_effect_id is not None
            if self._best_similarity is None or similarity > self._best_similarity:
                self._best_similarity = similarity
            if progressed:
                self._progress_evidence += 1
                self._consecutive_mismatches = 0
                intent.last_progress_tick = int(tick)
                if (
                    similarity >= threshold
                    and self._progress_evidence >= self.policy.minimum_progress_evidence
                ):
                    self.last_prediction_match = similarity
                    return self._terminate(
                        intent,
                        IntentStatus.SATISFIED,
                        reason=ANTICIPATED_EFFECT_OBSERVED,
                        tick=tick,
                        observed_effect_id=observed_effect_id,
                        similarity=similarity,
                    )
            elif mismatched and not (self._expected_atoms and self._observed_atoms):
                # A single mismatch leaves room for controller correction (§67).
                self._consecutive_mismatches += 1
                if self._consecutive_mismatches >= self.policy.max_consecutive_mismatches:
                    return self._terminate(
                        intent,
                        IntentStatus.FAILED,
                        reason=REPEATED_HIGH_MISMATCH,
                        tick=tick,
                        observed_effect_id=observed_effect_id,
                        similarity=similarity,
                    )

        if commitment_status is not None and commitment_status is not CommitmentStatus.ACTIVE:
            if commitment_status is CommitmentStatus.COMPLETED:
                if not self.policy.reconcile_observed_effects:
                    return self._terminate(
                        intent,
                        IntentStatus.SATISFIED,
                        reason=COMMITMENT_COMPLETED_UNVERIFIED,
                        tick=tick,
                    )
                return self._terminate(
                    intent, IntentStatus.FAILED, reason=COMPETENCE_EXHAUSTED, tick=tick
                )
            if commitment_status is CommitmentStatus.FAILED:
                return self._terminate(
                    intent, IntentStatus.FAILED, reason=CONTROLLER_TERMINAL_FAILURE, tick=tick
                )
            if commitment_status is CommitmentStatus.INCOMPATIBLE:
                return self._terminate(
                    intent, IntentStatus.INVALIDATED, reason=SURFACE_INCOMPATIBLE, tick=tick
                )
            if commitment_status is CommitmentStatus.INVALIDATED:
                return self._terminate(
                    intent, IntentStatus.INVALIDATED, reason=CAUSAL_BINDING_INVALIDATED, tick=tick
                )
            return self._terminate(
                intent, IntentStatus.FAILED, reason=COMMITMENT_TERMINAL_FAILURE, tick=tick
            )

        if (
            self.policy.reconcile_observed_effects
            and int(tick) - intent.last_progress_tick >= self.policy.stagnation_ticks
        ):
            return self._terminate(intent, IntentStatus.FAILED, reason=STAGNATION, tick=tick)
        return None

    # -- read views ----------------------------------------------------------------
    @property
    def satisfied_count(self) -> int:
        return self.counts[IntentStatus.SATISFIED]

    def age(self, tick: int) -> int | None:
        return None if self.active is None else max(0, int(tick) - self.active.created_tick)

    def last_progress_age(self, tick: int) -> int | None:
        return None if self.active is None else max(0, int(tick) - self.active.last_progress_tick)

    # -- persistence -------------------------------------------------------------
    def checkpoint(self) -> dict[str, object]:
        """Only the live intent; terminal history belongs to traces/Observatory (§82.4)."""
        live = self.active if self.active is not None and not self.active.terminal else None
        return {
            "schema_version": self.SCHEMA_VERSION,
            "active": live.checkpoint() if live is not None else None,
            "active_commitment_id": self.active_commitment_id if live is not None else None,
            "progress_evidence": self._progress_evidence if live is not None else 0,
            "consecutive_mismatches": self._consecutive_mismatches if live is not None else 0,
            "reconciliation_trace": (
                {
                    "binding_valid_at_start": self._binding_valid_at_start,
                    "best_similarity": self._best_similarity,
                    "mismatch_sum": self._mismatch_sum,
                    "mismatch_count": self._mismatch_count,
                    "expected_atoms": list(self._expected_atoms),
                    "observed_atoms": sorted(self._observed_atoms),
                }
                if live is not None
                else None
            ),
            "formed": self._formed,
            "counts": {status.value: count for status, count in self.counts.items()},
            "outcome_evidence": self.outcome_ledger.checkpoint(),
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, Any] | None,
        *,
        organism_id: str,
        policy: IntentionPolicy | None = None,
    ) -> "IntentionDomain":
        obj = cls(organism_id=organism_id, policy=policy)
        if payload is None:
            return obj
        version = payload.get("schema_version")
        if version not in (1, cls.SCHEMA_VERSION):
            raise ValueError("unsupported executive intention checkpoint")
        raw_active = payload.get("active")
        if raw_active is not None:
            if not isinstance(raw_active, Mapping):
                raise ValueError("invalid executive intention")
            intent = ActionIntent.restore(raw_active)
            if intent.terminal:
                raise ValueError("a checkpointed live intent cannot be terminal")
            obj.active = intent
            commitment = payload.get("active_commitment_id")
            obj.active_commitment_id = str(commitment) if commitment is not None else None
            if intent.status is IntentStatus.ACTIVE and obj.active_commitment_id is None:
                raise ValueError("an active intent must reference its commitment")
            obj._progress_evidence = int(payload.get("progress_evidence", 0))
            obj._consecutive_mismatches = int(payload.get("consecutive_mismatches", 0))
            trace = payload.get("reconciliation_trace")
            if isinstance(trace, Mapping):
                obj._binding_valid_at_start = bool(trace.get("binding_valid_at_start", False))
                best = trace.get("best_similarity")
                obj._best_similarity = None if best is None else float(best)
                obj._mismatch_sum = float(trace.get("mismatch_sum", 0.0))
                obj._mismatch_count = int(trace.get("mismatch_count", 0))
                obj._expected_atoms = tuple(str(a) for a in trace.get("expected_atoms", ()))
                obj._observed_atoms = {str(a) for a in trace.get("observed_atoms", ())}
        obj._formed = int(payload.get("formed", 0))
        raw_counts = payload.get("counts", {})
        if isinstance(raw_counts, Mapping):
            for status in obj.counts:
                obj.counts[status] = int(raw_counts.get(status.value, 0))
        # Schema 1 (Agency Acquisition v1) had no executive outcome evidence.
        obj.outcome_ledger = ExecutiveOutcomeLedger.restore(payload.get("outcome_evidence"))
        return obj


__all__ = [
    "ExecutiveMode",
    "IntentOutcome",
    "IntentionDomain",
    "IntentionPolicy",
]
