"""Universal Sensorimotor v2 action arbitration."""
from __future__ import annotations

from dataclasses import dataclass

from .action import ActionProposal, ActionSource
from .commitment import ActionCommitment, CommitmentStatus


@dataclass(frozen=True, slots=True)
class ArbitrationDecision:
    proposal: ActionProposal | None
    keep_current: bool
    reason: str


class ActionArbitrator:
    """Select commitments without collapsing evaluations to a hand-written reward."""

    def choose(
        self,
        *,
        proposals: tuple[ActionProposal, ...],
        current: ActionCommitment | None = None,
        tick: int,
    ) -> ArbitrationDecision:
        valid = [
            proposal
            for proposal in proposals
            if (proposal.evaluation.estimated_risk or 0.0) < 1.0
        ]
        protective = [
            proposal
            for proposal in valid
            if proposal.source is ActionSource.PROTECTION
            and proposal.evaluation.protective_relevance > 0.0
        ]
        if protective:
            chosen = max(
                protective,
                key=lambda p: (
                    p.evaluation.protective_relevance,
                    p.evaluation.homeostatic_relevance,
                    p.proposal_id,
                ),
            )
            return ArbitrationDecision(chosen, False, "protective_dominance")

        if current is not None and current.active:
            age = max(0, tick - current.started_tick)
            if age < current.minimum_duration:
                return ArbitrationDecision(None, True, "minimum_commitment")
            if current.maximum_duration is None or age < current.maximum_duration:
                # A selected temporally-extended action owns control until it
                # completes/fails/expires. Ordinary new proposals do not force
                # deliberation every physical tick.
                return ArbitrationDecision(None, True, "continue_commitment")

        if not valid:
            return ArbitrationDecision(None, current is not None and current.active, "no_valid_proposal")

        # Established/prospective control dominates open-ended exploration when
        # the organism itself has activated that competence.  This is source
        # dominance, not a weighted reward sum.
        learned = [
            proposal
            for proposal in valid
            if proposal.source in {ActionSource.PROSPECTION, ActionSource.COMPETENCE}
            and proposal.competence_id is not None
        ]
        if learned:
            chosen = max(
                learned,
                key=lambda p: (
                    p.evaluation.effect_confidence,
                    p.evaluation.controllability
                    if p.evaluation.controllability is not None
                    else -1.0,
                    -(p.evaluation.uncertainty),
                    p.proposal_id,
                ),
            )
            return ArbitrationDecision(chosen, False, "learned_control")

        regulatory = [
            proposal
            for proposal in valid
            if proposal.source is ActionSource.REGULATION
        ]
        if regulatory:
            chosen = max(
                regulatory,
                key=lambda p: (
                    p.evaluation.homeostatic_relevance,
                    p.evaluation.effect_confidence,
                    p.proposal_id,
                ),
            )
            return ArbitrationDecision(chosen, False, "regulatory_control")

        exploratory = [
            proposal
            for proposal in valid
            if proposal.source is ActionSource.EXPLORATION
        ]
        if exploratory:
            chosen = max(
                exploratory,
                key=lambda p: (
                    p.evaluation.epistemic_relevance,
                    p.evaluation.uncertainty,
                    p.proposal_id,
                ),
            )
            return ArbitrationDecision(chosen, False, "epistemic_exploration")

        chosen = sorted(valid, key=lambda p: p.proposal_id)[0]
        return ArbitrationDecision(chosen, False, "selected")
