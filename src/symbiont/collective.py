from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class SourceVote:
    threat: bool
    confidence: float


@dataclass(slots=True)
class SourceTrust:
    score: float = 0.75
    evaluations: int = 0


@dataclass(slots=True)
class PatternEvidence:
    reports: int = 0
    votes: dict[str, SourceVote] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class OpenQuestion:
    fingerprint: str
    reports: int
    sources: int
    threat_probability: float
    certainty: float


@dataclass(slots=True)
class CollectiveMemory:
    patterns: dict[str, PatternEvidence] = field(default_factory=dict)
    source_trust: dict[str, SourceTrust] = field(default_factory=dict)

    def report(self, fingerprint: str, threat: bool, confidence: float, source: str) -> None:
        ev = self.patterns.setdefault(fingerprint, PatternEvidence())
        ev.reports += 1
        ev.votes[source] = SourceVote(
            threat=threat,
            confidence=min(max(confidence, 0.05), 1.0),
        )
        self.source_trust.setdefault(source, SourceTrust())

    def trust(self, source: str) -> float:
        return self.source_trust.get(source, SourceTrust()).score

    def belief(self, fingerprint: str) -> tuple[float, float]:
        ev = self.patterns.get(fingerprint)
        if ev is None or not ev.votes:
            return 0.5, 0.0

        threat_weight = 0.0
        total_weight = 0.0
        confidence_sum = 0.0
        trust_sum = 0.0
        for source, vote in ev.votes.items():
            trust = self.trust(source)
            weight = trust * vote.confidence
            total_weight += weight
            threat_weight += weight * int(vote.threat)
            confidence_sum += vote.confidence
            trust_sum += trust

        probability = threat_weight / max(total_weight, 1e-9)
        diversity = min(len(ev.votes) / 10.0, 1.0)
        avg_confidence = confidence_sum / len(ev.votes)
        avg_trust = trust_sum / len(ev.votes)
        agreement = abs(probability - 0.5) * 2.0
        certainty = min(
            1.0,
            0.35 * diversity
            + 0.25 * avg_confidence
            + 0.25 * agreement
            + 0.15 * avg_trust,
        )
        return probability, certainty

    def confidence(self, fingerprint: str) -> float:
        return self.belief(fingerprint)[1]

    def recalibrate_sources(self, min_peers: int = 4) -> None:
        """Update source trust from agreement with independent peer consensus.

        No simulator ground truth is used. This is deliberately imperfect: the
        experiment can therefore study collusion and poisoning rather than assume
        a trusted oracle.
        """
        for source, trust_state in self.source_trust.items():
            agreements: list[float] = []
            for ev in self.patterns.values():
                own_vote = ev.votes.get(source)
                if own_vote is None or len(ev.votes) - 1 < min_peers:
                    continue

                peer_threat = 0.0
                peer_total = 0.0
                for peer, vote in ev.votes.items():
                    if peer == source:
                        continue
                    weight = self.trust(peer) * vote.confidence
                    peer_total += weight
                    peer_threat += weight * int(vote.threat)
                if peer_total <= 0:
                    continue
                peer_belief = peer_threat / peer_total >= 0.5
                agreements.append(float(own_vote.threat == peer_belief))

            if not agreements:
                continue
            agreement_rate = sum(agreements) / len(agreements)
            target = 0.20 + 0.75 * agreement_rate
            trust_state.score = min(0.98, max(0.15, 0.90 * trust_state.score + 0.10 * target))
            trust_state.evaluations += 1

    @property
    def mean_source_trust(self) -> float:
        if not self.source_trust:
            return 0.0
        return sum(v.score for v in self.source_trust.values()) / len(self.source_trust)

    def low_trust_sources(self, threshold: float = 0.45) -> int:
        return sum(v.score < threshold for v in self.source_trust.values())

    def open_questions(self, min_reports: int = 4) -> list[OpenQuestion]:
        questions: list[OpenQuestion] = []
        for fp, ev in self.patterns.items():
            probability, certainty = self.belief(fp)
            if ev.reports >= min_reports and certainty < 0.62:
                questions.append(
                    OpenQuestion(
                        fingerprint=fp,
                        reports=ev.reports,
                        sources=len(ev.votes),
                        threat_probability=probability,
                        certainty=certainty,
                    )
                )
        return sorted(questions, key=lambda q: (-q.reports, q.certainty))
