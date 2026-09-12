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
    seen_evidence: set[tuple[str, str]] = field(default_factory=set, repr=False)


@dataclass(slots=True, frozen=True)
class InheritedPrior:
    threat_probability: float
    certainty: float
    generation: int
    support: int


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
    inherited_priors: dict[str, InheritedPrior] = field(default_factory=dict)
    _pending_source_revisions: dict[str, set[str]] = field(default_factory=dict, repr=False)

    def report(
        self,
        fingerprint: str,
        threat: bool,
        confidence: float,
        source: str,
        *,
        evidence_id: str | None = None,
    ) -> bool:
        """Record one source revision and return whether it was fresh evidence.

        Live consensus stores the latest vote per source. Replaying the same
        evidence identity is ignored. Callers without explicit identities retain
        compatibility: an identical latest vote is treated as a replay, while a
        changed vote is a new revision. The simulator supplies event identities,
        so repeated observations at different steps remain distinct evidence.
        """
        ev = self.patterns.setdefault(fingerprint, PatternEvidence())
        vote = SourceVote(
            threat=threat,
            confidence=min(max(confidence, 0.05), 1.0),
        )

        if evidence_id is not None:
            evidence_key = (source, str(evidence_id))
            if evidence_key in ev.seen_evidence:
                return False
            ev.seen_evidence.add(evidence_key)
        elif ev.votes.get(source) == vote:
            return False

        ev.reports += 1
        ev.votes[source] = vote
        self.source_trust.setdefault(source, SourceTrust())
        self._pending_source_revisions.setdefault(fingerprint, set()).add(source)
        return True

    def inherit(
        self,
        fingerprint: str,
        threat_probability: float,
        certainty: float,
        *,
        generation: int,
        support: int,
    ) -> None:
        """Install a bounded prior without fabricating live reporters or trust."""
        self.inherited_priors[fingerprint] = InheritedPrior(
            threat_probability=min(0.98, max(0.02, float(threat_probability))),
            certainty=min(0.55, max(0.0, float(certainty))),
            generation=max(0, int(generation)),
            support=max(0, int(support)),
        )

    def trust(self, source: str) -> float:
        return self.source_trust.get(source, SourceTrust()).score

    def live_belief(self, fingerprint: str) -> tuple[float, float]:
        """Belief derived only from current-generation reports."""
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

    def belief(self, fingerprint: str) -> tuple[float, float]:
        """Combine a weak inherited prior with current-generation evidence."""
        live_probability, live_certainty = self.live_belief(fingerprint)
        prior = self.inherited_priors.get(fingerprint)
        if prior is None:
            return live_probability, live_certainty
        if live_certainty <= 0:
            return prior.threat_probability, prior.certainty

        prior_weight = prior.certainty * 0.65
        live_weight = max(live_certainty, 0.15)
        probability = (
            live_probability * live_weight
            + prior.threat_probability * prior_weight
        ) / (live_weight + prior_weight)
        certainty = min(
            1.0,
            live_certainty + 0.18 * prior.certainty * (1.0 - live_certainty),
        )
        return probability, certainty

    def confidence(self, fingerprint: str) -> float:
        return self.belief(fingerprint)[1]

    @property
    def inherited_count(self) -> int:
        return len(self.inherited_priors)

    def recalibrate_sources(self, min_peers: int = 4) -> None:
        """Consume each fresh source revision at most once.

        Peer consensus remains intentionally imperfect and uses no simulator
        ground truth or inherited prior. A new revision for one source evaluates
        that source against its current peers; it does not replay every historical
        vote in the pattern. Identical evidence replays are rejected by report().
        """
        if not self._pending_source_revisions:
            return

        agreements_by_source: dict[str, list[float]] = {}
        for fingerprint, pending_sources in self._pending_source_revisions.items():
            ev = self.patterns.get(fingerprint)
            if ev is None:
                continue
            for source in pending_sources:
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
                agreements_by_source.setdefault(source, []).append(
                    float(own_vote.threat == peer_belief)
                )

        for source, agreements in agreements_by_source.items():
            trust_state = self.source_trust[source]
            for agreement in agreements:
                target = 0.20 + 0.75 * agreement
                trust_state.score = min(
                    0.98,
                    max(0.15, 0.90 * trust_state.score + 0.10 * target),
                )
            trust_state.evaluations += len(agreements)

        self._pending_source_revisions.clear()

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
