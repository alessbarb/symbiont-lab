from __future__ import annotations

from dataclasses import asdict, dataclass

from ..social.ledger import SocialEvidenceLedger, SocialQuestion


@dataclass(slots=True, frozen=True)
class Hypothesis:
    """A bounded explanation over synthetic aggregate state only."""

    claim_ref: str
    title: str
    confidence: float
    priority: float
    rationale: str
    questions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ReasoningEngine:
    """Turn unresolved social claims into testable, non-operational questions.

    The engine has no tools and cannot execute actions. It receives only
    claim references and descriptive evidence from the social ledger.
    """

    def analyze(self, ledger: SocialEvidenceLedger, limit: int = 3) -> tuple[Hypothesis, ...]:
        candidates = [self._build(question) for question in ledger.open_questions()]
        candidates.sort(key=lambda h: (-h.priority, h.claim_ref))
        return tuple(candidates[:limit])

    def _build(self, question: SocialQuestion) -> Hypothesis:
        title = "socially unresolved claim"
        rationale = "There is a socially transmitted claim that has not been empirically verified or contradicted by the organism's own experience."

        evidence = min(
            (question.independent_support_roots + question.independent_contradiction_roots) / 10.0,
            1.0,
        )
        confidence = min(1.0, (1.0 - question.uncertainty) * (0.65 + 0.35 * evidence))
        priority = min(1.0, question.uncertainty * (0.45 + 0.55 * evidence))

        questions = (
            "Does independent evidence lineages differ systematically on this claim?",
            "Can local empirical validation support this claim?",
            "Are there compatibility factors affecting the divergence of opinions on this claim?",
        )
        return Hypothesis(
            claim_ref=question.claim_ref,
            title=title,
            confidence=confidence,
            priority=priority,
            rationale=rationale,
            questions=questions,
        )
