from __future__ import annotations

from dataclasses import dataclass, field

from .beliefs import BeliefModel
from .collective import CollectiveMemory
from .memory import AgentMemory, Episode
from .model import Assessment, HostModel, Observation, fingerprint


@dataclass(slots=True)
class Agent:
    agent_id: str
    model: HostModel = field(default_factory=HostModel)
    memory: AgentMemory = field(default_factory=AgentMemory)
    beliefs: BeliefModel = field(default_factory=BeliefModel)
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
        local_threat, local_certainty = self.beliefs.belief(fp)
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

        local_weight = 0.12 * local_certainty
        combined_suspicion = min(
            1.0,
            max(
                0.0,
                (
                    0.72 * risk
                    + 0.18 * novelty
                    + 0.10 * collective_threat * collective_certainty
                    + local_weight * local_threat
                )
                / (1.0 + local_weight),
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
            local_threat=local_threat,
            local_certainty=local_certainty,
        )

    def observe(self, step: int, obs: Observation, collective: CollectiveMemory) -> Assessment:
        self.memory.forget(step)
        assessment = self.assess(obs, collective)
        self.beliefs.revise(
            fingerprint=assessment.fingerprint,
            probability=assessment.threat_probability or 0.0,
            confidence=max(
                0.05,
                0.70 * (1.0 - assessment.uncertainty) + 0.30 * assessment.novelty,
            ),
            step=step,
        )

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
                evidence_id=f"step:{step}",
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
