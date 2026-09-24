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

    @property
    def primitive_id(self) -> str | None:
        """Legacy read shim; v2 does not arbitrate primitive ids."""
        return None


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
                if not valid:
                    return ArbitrationDecision(None, True, "continue_commitment")

        if not valid:
            return ArbitrationDecision(None, current is not None and current.active, "no_valid_proposal")

        # Contextual lexicographic ordering: physiology first, then epistemic
        # relevance, then confidence.  No hidden scalar reward is introduced.
        chosen = max(
            valid,
            key=lambda p: (
                p.evaluation.homeostatic_relevance,
                p.evaluation.epistemic_relevance,
                p.evaluation.effect_confidence,
                -(p.evaluation.estimated_cost or 0.0),
                p.proposal_id,
            ),
        )
        return ArbitrationDecision(chosen, False, "selected")

    def choose_reactive(self, *, state, memory, candidate_ids: tuple[str, ...]):
        """Compatibility shim for v1 callers during checkpoint migration.

        It never executes motors; it only reports a learned candidate id.
        """
        from symbiont.core.regulation.arbitration_legacy import LegacyArbitrationDecision
        if float(state.withdrawal) < 0.55:
            return LegacyArbitrationDecision(None, "ordinary")
        candidate = memory.best(signature=state.signature, candidates=candidate_ids)
        if candidate is None:
            return LegacyArbitrationDecision(None, "acute_no_learned_response")
        return LegacyArbitrationDecision(candidate, "reactive_learned_relief")
