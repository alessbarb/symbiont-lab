from __future__ import annotations

from dataclasses import asdict, dataclass

from ..social.ledger import SocialEvidenceLedger
from .reasoning import Hypothesis


@dataclass(slots=True, frozen=True)
class CuriosityProbe:
    """A shadow-only counterfactual question. It never acts on a host."""

    source_claim: str
    counterfactual_claim: str
    feature: str
    change: str
    expected_information_gain: float
    expected_cost: float
    utility: float
    question: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CuriosityPlanner:
    """Rank safe synthetic counterfactuals by expected information gain.

    The planner sees only coarse fingerprints, hypotheses and social ledger state.
    It cannot inspect or modify a host, run commands, or access evaluator truth.
    """

    def plan(
        self,
        hypotheses: tuple[Hypothesis, ...],
        ledger: SocialEvidenceLedger,
        limit: int = 3,
    ) -> tuple[CuriosityProbe, ...]:
        candidates: list[CuriosityProbe] = []
        for hypothesis in hypotheses:
            candidates.extend(self._probes_for(hypothesis, ledger))
        candidates.sort(
            key=lambda probe: (-probe.utility, probe.feature, probe.counterfactual_claim)
        )
        return tuple(candidates[: max(0, limit)])

    def _probes_for(
        self,
        hypothesis: Hypothesis,
        ledger: SocialEvidenceLedger,
    ) -> list[CuriosityProbe]:
        claim = ledger.claims.get(hypothesis.claim_ref)
        if not claim:
            return []

        # Simplified for now: if we have a claim, we're curious about resolving it
        # depending on its independent disagreement, novelty, unresolvedness
        state = ledger.source_states.get(claim.source_id)
        if not state:
            return []

        unresolvedness = state.unresolved / max(1, len(state.samples))
        evidence_diversity = (state.agreements + state.contradictions) / max(1, len(state.samples))
        local_evidence_gap = 1.0  # Placeholder, as the claim is unverified

        information_gain = unresolvedness * evidence_diversity * local_evidence_gap
        expected_cost = 0.10
        utility = min(1.0, information_gain / (0.55 + expected_cost))

        return [
            CuriosityProbe(
                source_claim=hypothesis.claim_ref,
                counterfactual_claim="derived-claim",
                feature="social_claim",
                change="resolve",
                expected_information_gain=information_gain,
                expected_cost=expected_cost,
                utility=utility,
                question="Can this claim be empirically validated?",
            )
        ]
