from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_evidence import SourceEvidenceOutcome, SourceEvidenceSample, SourceEvidenceState


@dataclass(frozen=True, slots=True)
class SocialClaim:
    claim_id: str
    source_id: str
    root_evidence_ids: frozenset[str]
    parent_claim_ids: frozenset[str]
    payload: Any  # Native relation representation
    received_tick: int
    freshness: float


@dataclass(slots=True)
class SocialEvidenceLedger:
    claims: dict[str, SocialClaim] = field(default_factory=dict)
    source_states: dict[str, SourceEvidenceState] = field(default_factory=dict)
    reconciliations: dict[str, SourceEvidenceOutcome] = field(default_factory=dict)

    def receive_claim(self, claim: SocialClaim) -> None:
        if claim.claim_id not in self.claims:
            self.claims[claim.claim_id] = claim
            if claim.source_id not in self.source_states:
                self.source_states[claim.source_id] = SourceEvidenceState(source_id=claim.source_id)

    def assess_claim(self, claim_id: str) -> SourceEvidenceOutcome:
        """Returns the current known assessment for a claim, defaulting to UNRESOLVED."""
        return self.reconciliations.get(claim_id, SourceEvidenceOutcome.UNRESOLVED)

    def record_local_reconciliation(
        self,
        claim_id: str,
        tick: int,
        outcome: SourceEvidenceOutcome,
        compatibility: float,
        quality: float,
        freshness: float,
        evidence_ref: str | None,
    ) -> None:
        """Record real empirical validation against a social claim."""
        if claim_id not in self.claims:
            raise ValueError(f"Unknown claim: {claim_id}")

        claim = self.claims[claim_id]
        self.reconciliations[claim_id] = outcome
        
        sample = SourceEvidenceSample(
            tick=tick,
            outcome=outcome,
            compatibility=compatibility,
            quality=quality,
            freshness=freshness,
            independence=1.0,  # Could be derived from root_evidence_ids
            evidence_ref=evidence_ref,
        )
        self.source_states[claim.source_id].add_sample(sample)

    def claim_evidence(self, claim_id: str) -> dict[str, Any]:
        """Expose descriptive evidence about a claim."""
        claim = self.claims.get(claim_id)
        if not claim:
            return {}
        return {
            "claim": claim,
            "outcome": self.assess_claim(claim_id),
            "source_reliability": self.source_states[claim.source_id].source_reliability,
        }

    def unresolved_claims(self) -> list[SocialClaim]:
        """Return claims that have no local reconciliation yet."""
        return [
            claim for claim_id, claim in self.claims.items()
            if self.assess_claim(claim_id) == SourceEvidenceOutcome.UNRESOLVED
        ]

    def open_questions(self) -> list[SocialQuestion]:
        """Convert unresolved or highly contested claims into SocialQuestions."""
        questions = []
        for claim_id, claim in self.claims.items():
            outcome = self.assess_claim(claim_id)
            if outcome == SourceEvidenceOutcome.UNRESOLVED:
                state = self.source_states[claim.source_id]
                questions.append(
                    SocialQuestion(
                        claim_ref=claim_id,
                        independent_support_roots=state.agreements,
                        independent_contradiction_roots=state.contradictions,
                        unresolved_roots=state.unresolved,
                        compatibility=state.mean_compatibility,
                        freshness=state.mean_freshness,
                        uncertainty=1.0 - state.source_reliability,
                    )
                )
        return questions

@dataclass(slots=True, frozen=True)
class SocialQuestion:
    claim_ref: str
    independent_support_roots: int
    independent_contradiction_roots: int
    unresolved_roots: int
    compatibility: float
    freshness: float
    uncertainty: float

