from __future__ import annotations

from dataclasses import asdict, dataclass

from ..social.collective import CollectiveMemory, OpenQuestion
from ..foundation.model import FEATURES


@dataclass(slots=True, frozen=True)
class Hypothesis:
    """A bounded explanation over synthetic aggregate state only."""

    fingerprint: str
    title: str
    confidence: float
    priority: float
    rationale: str
    questions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ReasoningEngine:
    """Turn unresolved collective patterns into testable, non-operational questions.

    The engine has no tools and cannot execute actions. It receives only coarse
    fingerprints and aggregate collective beliefs produced by the simulator.
    """

    def analyze(self, collective: CollectiveMemory, limit: int = 3) -> tuple[Hypothesis, ...]:
        candidates = [self._build(question) for question in collective.open_questions()]
        candidates.sort(key=lambda h: (-h.priority, h.fingerprint))
        return tuple(candidates[:limit])

    def _build(self, question: OpenQuestion) -> Hypothesis:
        bins = question.fingerprint.split("-")
        levels = dict(zip(FEATURES, bins))
        high = [name for name, level in levels.items() if level == "H"]
        elevated = [name for name, level in levels.items() if level in {"M", "H"}]

        if levels.get("file_changes") == "H" and levels.get("persistence_changes") in {"M", "H"}:
            title = "integrity-change cluster"
            rationale = "High synthetic file-change activity co-occurs with elevated persistence change, but the population still disagrees about its meaning."
        elif levels.get("network") == "H" and levels.get("persistence_changes") in {"M", "H"}:
            title = "persistent-network cluster"
            rationale = "High synthetic network activity appears with elevated persistence behavior and insufficient collective certainty."
        elif levels.get("new_processes") == "H" and levels.get("persistence_changes") == "H":
            title = "process-persistence cluster"
            rationale = "New-process and persistence signals rise together, while peer evidence remains inconclusive."
        else:
            title = "mixed unresolved behavior"
            rationale = "The coarse synthetic pattern recurs often enough to matter but does not match a dominant explanatory template."

        uncertainty = 1.0 - question.certainty
        evidence = min(question.sources / 10.0, 1.0)
        confidence = min(1.0, question.certainty * (0.65 + 0.35 * evidence))
        priority = min(1.0, uncertainty * (0.45 + 0.55 * evidence))

        focus = high[0] if high else (elevated[0] if elevated else FEATURES[0])
        questions = (
            f"Does disagreement fall when {focus} is one synthetic intensity bin lower while the other features stay comparable?",
            f"Does this fingerprint recur across host profiles with different baseline {focus} levels?",
            "Do high-trust and low-trust reporters disagree systematically on this same fingerprint?",
        )
        return Hypothesis(
            fingerprint=question.fingerprint,
            title=title,
            confidence=confidence,
            priority=priority,
            rationale=rationale,
            questions=questions,
        )
