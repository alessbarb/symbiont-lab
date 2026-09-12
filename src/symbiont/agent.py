from __future__ import annotations

from dataclasses import dataclass, field

from .collective import CollectiveMemory
from .model import Assessment, HostModel, Observation, fingerprint


@dataclass(slots=True)
class Episode:
    step: int
    fingerprint: str
    curiosity: float
    risk: float
    label: str


@dataclass(slots=True)
class Agent:
    agent_id: str
    model: HostModel = field(default_factory=HostModel)
    episodes: list[Episode] = field(default_factory=list)
    investigated: int = 0
    true_positive_investigations: int = 0
    false_positive_investigations: int = 0

    def assess(self, obs: Observation, collective: CollectiveMemory) -> Assessment:
        novelty = self.model.novelty(obs)

        # Risk combines disruptive signals but deliberately remains probabilistic.
        risk = min(
            1.0,
            0.12 * obs.cpu
            + 0.18 * obs.network
            + 0.28 * obs.file_changes
            + 0.16 * obs.new_processes
            + 0.26 * obs.persistence_changes,
        )

        # Immature models admit uncertainty instead of pretending to know.
        maturity = self.model.maturity
        collective_conf = collective.confidence(fingerprint(obs))
        uncertainty = min(1.0, (1.0 - maturity) * 0.55 + (1.0 - collective_conf) * 0.45)

        # Relevance approximates potential impact on integrity/availability.
        relevance = min(
            1.0,
            0.15 * obs.cpu
            + 0.15 * obs.network
            + 0.35 * obs.file_changes
            + 0.10 * obs.new_processes
            + 0.25 * obs.persistence_changes,
        )

        # A novel pattern loses information value once the collective already understands it.
        information_gain = novelty * (1.0 - collective_conf)
        curiosity = novelty * uncertainty * information_gain * max(relevance, 0.05)

        should_investigate = (
            self.model.maturity >= 0.5
            and (risk >= 0.45 or curiosity >= 0.035)
        )

        return Assessment(
            novelty=novelty,
            uncertainty=uncertainty,
            relevance=relevance,
            information_gain=information_gain,
            curiosity=curiosity,
            risk=risk,
            fingerprint=fingerprint(obs),
            should_investigate=should_investigate,
        )

    def observe(self, step: int, obs: Observation, collective: CollectiveMemory) -> Assessment:
        assessment = self.assess(obs, collective)

        if assessment.should_investigate:
            self.investigated += 1
            is_threat = obs.label.startswith("pathogen")
            if is_threat:
                self.true_positive_investigations += 1
            else:
                self.false_positive_investigations += 1

            self.episodes.append(
                Episode(
                    step=step,
                    fingerprint=assessment.fingerprint,
                    curiosity=assessment.curiosity,
                    risk=assessment.risk,
                    label=obs.label,
                )
            )
            collective.report(
                fingerprint=assessment.fingerprint,
                threat=is_threat,
                confidence=max(assessment.risk, assessment.curiosity),
                source=self.agent_id,
            )

        # Learn normality conservatively: strongly suspicious observations do not redefine normal.
        if assessment.risk < 0.50 and not obs.label.startswith("pathogen"):
            self.model.update(obs)

        # Bootstrap baseline before there is enough context to assess novelty.
        if self.model.maturity < 0.5 and not obs.label.startswith("pathogen"):
            self.model.update(obs)

        return assessment
