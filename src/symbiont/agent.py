from __future__ import annotations

from dataclasses import dataclass, field

from .collective import CollectiveMemory
from .memory import AgentMemory, Episode
from .model import Assessment, HostModel, Observation, fingerprint


@dataclass(slots=True)
class Agent:
    agent_id: str
    model: HostModel = field(default_factory=HostModel)
    memory: AgentMemory = field(default_factory=AgentMemory)
    investigated: int = 0
    risk_scale: float = 1.0
    curiosity_scale: float = 1.0
    investigation_bias: float = 0.0
    report_inversion: bool = False
    drift_streak: int = 0
    drift_adaptations: int = 0

    def assess(self, obs: Observation, collective: CollectiveMemory) -> Assessment:
        novelty = self.model.novelty(obs)
        fp = fingerprint(obs)
        collective_threat, collective_certainty = collective.belief(fp)

        raw_risk = min(
            1.0,
            0.12 * obs.cpu
            + 0.18 * obs.network
            + 0.28 * obs.file_changes
            + 0.16 * obs.new_processes
            + 0.26 * obs.persistence_changes,
        )
        risk = min(1.0, raw_risk * self.risk_scale)

        maturity = self.model.maturity
        uncertainty = min(
            1.0,
            (1.0 - maturity) * 0.38
            + (1.0 - collective_certainty) * 0.42
            + (1.0 - abs(risk - 0.5) * 2.0) * 0.20,
        )
        relevance = min(
            1.0,
            0.15 * obs.cpu
            + 0.15 * obs.network
            + 0.35 * obs.file_changes
            + 0.10 * obs.new_processes
            + 0.25 * obs.persistence_changes,
        )
        information_gain = novelty * (1.0 - collective_certainty)
        curiosity = min(
            1.0,
            novelty
            * uncertainty
            * information_gain
            * max(relevance, 0.05)
            * self.curiosity_scale,
        )

        combined_suspicion = min(
            1.0,
            max(
                0.0,
                0.72 * risk
                + 0.18 * novelty
                + 0.10 * collective_threat * collective_certainty,
            ),
        )
        should_investigate = self.model.maturity >= 0.5 and (
            combined_suspicion >= 0.43 + self.investigation_bias
            or curiosity >= max(0.012, 0.025 - self.investigation_bias * 0.25)
        )
        believes_threat = combined_suspicion >= 0.48 + self.investigation_bias * 0.5

        return Assessment(
            novelty=novelty,
            uncertainty=uncertainty,
            relevance=relevance,
            information_gain=information_gain,
            curiosity=curiosity,
            risk=risk,
            collective_threat=collective_threat,
            collective_certainty=collective_certainty,
            fingerprint=fp,
            threat_probability=combined_suspicion,
            should_investigate=should_investigate,
            believes_threat=believes_threat,
        )

    def observe(self, step: int, obs: Observation, collective: CollectiveMemory) -> Assessment:
        self.memory.forget(step)
        assessment = self.assess(obs, collective)

        if assessment.should_investigate:
            self.investigated += 1
            self.memory.remember(
                Episode(
                    step=step,
                    fingerprint=assessment.fingerprint,
                    curiosity=assessment.curiosity,
                    risk=assessment.risk,
                    believed_threat=assessment.believes_threat,
                )
            )
            reported_threat = assessment.believes_threat
            if self.report_inversion:
                reported_threat = not reported_threat
            collective.report(
                fingerprint=assessment.fingerprint,
                threat=reported_threat,
                confidence=max(
                    0.05,
                    abs(assessment.risk - 0.5) * 2.0,
                    assessment.collective_certainty * 0.6,
                ),
                source=self.agent_id,
            )

        drift_candidate = (
            self.model.maturity >= 0.5
            and assessment.novelty >= 0.45
            and assessment.risk < 0.45
            and assessment.collective_threat < 0.65
        )
        if drift_candidate:
            self.drift_streak += 1
        else:
            self.drift_streak = max(0, self.drift_streak - 1)

        # A sustained low-risk novelty can be a changed normal regime. The agent
        # adapts cautiously without access to simulator labels. This can still be
        # fooled, which is intentional and measurable in the laboratory.
        if self.drift_streak >= 5:
            self.model.update(obs)
            self.drift_adaptations += 1
            self.drift_streak = 2
        elif self.model.maturity < 0.5:
            self.model.update(obs)
        elif (
            not assessment.should_investigate
            and assessment.risk < 0.40
            and novelty_safe(assessment.novelty)
        ):
            self.model.update(obs)

        return assessment


def novelty_safe(novelty: float) -> bool:
    return novelty < 0.55
