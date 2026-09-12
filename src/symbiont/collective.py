from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PatternEvidence:
    reports: int = 0
    threat_votes: int = 0
    confidence_sum: float = 0.0
    sources: set[str] = field(default_factory=set)

    @property
    def confidence(self) -> float:
        if self.reports == 0:
            return 0.0
        diversity = min(len(self.sources) / 8.0, 1.0)
        vote_ratio = self.threat_votes / self.reports
        avg_conf = self.confidence_sum / self.reports
        return min(1.0, 0.45 * diversity + 0.35 * vote_ratio + 0.20 * avg_conf)


@dataclass(slots=True)
class OpenQuestion:
    fingerprint: str
    reports: int
    confidence: float


@dataclass(slots=True)
class CollectiveMemory:
    patterns: dict[str, PatternEvidence] = field(default_factory=dict)

    def report(self, fingerprint: str, threat: bool, confidence: float, source: str) -> None:
        ev = self.patterns.setdefault(fingerprint, PatternEvidence())
        ev.reports += 1
        ev.threat_votes += int(threat)
        ev.confidence_sum += confidence
        ev.sources.add(source)

    def confidence(self, fingerprint: str) -> float:
        ev = self.patterns.get(fingerprint)
        return ev.confidence if ev else 0.0

    def open_questions(self, min_reports: int = 3) -> list[OpenQuestion]:
        questions = []
        for fp, ev in self.patterns.items():
            conf = ev.confidence
            if ev.reports >= min_reports and conf < 0.60:
                questions.append(OpenQuestion(fp, ev.reports, conf))
        return sorted(questions, key=lambda q: (-q.reports, q.confidence))
