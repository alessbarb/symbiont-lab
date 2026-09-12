from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PatternEvidence:
    reports: int = 0
    threat_votes: int = 0
    confidence_sum: float = 0.0
    sources: set[str] = field(default_factory=set)

    @property
    def threat_probability(self) -> float:
        if self.reports == 0:
            return 0.5
        return self.threat_votes / self.reports

    @property
    def certainty(self) -> float:
        if self.reports == 0:
            return 0.0
        diversity = min(len(self.sources) / 10.0, 1.0)
        avg_conf = self.confidence_sum / self.reports
        agreement = abs(self.threat_probability - 0.5) * 2.0
        return min(1.0, 0.40 * diversity + 0.30 * avg_conf + 0.30 * agreement)


@dataclass(slots=True, frozen=True)
class OpenQuestion:
    fingerprint: str
    reports: int
    threat_probability: float
    certainty: float


@dataclass(slots=True)
class CollectiveMemory:
    patterns: dict[str, PatternEvidence] = field(default_factory=dict)

    def report(self, fingerprint: str, threat: bool, confidence: float, source: str) -> None:
        ev = self.patterns.setdefault(fingerprint, PatternEvidence())
        ev.reports += 1
        ev.threat_votes += int(threat)
        ev.confidence_sum += min(max(confidence, 0.0), 1.0)
        ev.sources.add(source)

    def belief(self, fingerprint: str) -> tuple[float, float]:
        ev = self.patterns.get(fingerprint)
        if ev is None:
            return 0.5, 0.0
        return ev.threat_probability, ev.certainty

    def confidence(self, fingerprint: str) -> float:
        """Compatibility helper: certainty that the collective understands a pattern."""
        return self.belief(fingerprint)[1]

    def open_questions(self, min_reports: int = 4) -> list[OpenQuestion]:
        questions: list[OpenQuestion] = []
        for fp, ev in self.patterns.items():
            if ev.reports >= min_reports and ev.certainty < 0.62:
                questions.append(
                    OpenQuestion(
                        fingerprint=fp,
                        reports=ev.reports,
                        threat_probability=ev.threat_probability,
                        certainty=ev.certainty,
                    )
                )
        return sorted(questions, key=lambda q: (-q.reports, q.certainty))
