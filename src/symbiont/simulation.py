from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Callable

from .agent import Agent
from .collective import CollectiveMemory
from .world import benign_event, make_profiles, pathogen_event


@dataclass(slots=True, frozen=True)
class SimulationSnapshot:
    step: int
    total_steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positives: int
    false_positives: int
    false_negatives: int
    detection_rate: float
    precision: float
    false_positive_rate: float
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(slots=True)
class SimulationResult:
    hosts: int
    steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positive_investigations: int
    false_positive_investigations: int
    false_negatives: int
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float

    @property
    def detection_rate(self) -> float:
        return self.true_positive_investigations / max(self.pathogen_events, 1)

    @property
    def precision(self) -> float:
        return self.true_positive_investigations / max(self.investigated, 1)

    @property
    def false_positive_rate(self) -> float:
        return self.false_positive_investigations / max(self.benign_events, 1)


@dataclass(slots=True)
class Evaluator:
    pathogen_events: int = 0
    benign_events: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    def record(self, *, is_threat: bool, investigated: bool) -> None:
        if is_threat:
            self.pathogen_events += 1
            if investigated:
                self.true_positives += 1
            else:
                self.false_negatives += 1
        else:
            self.benign_events += 1
            if investigated:
                self.false_positives += 1


def _make_agents(
    hosts: int,
    rng: random.Random,
    poison_fraction: float,
    heterogeneity: float,
) -> tuple[list[Agent], set[str]]:
    poison_count = min(hosts, max(0, round(hosts * poison_fraction)))
    poisoned_indexes = set(rng.sample(range(hosts), poison_count)) if poison_count else set()
    agents: list[Agent] = []
    poisoned_ids: set[str] = set()
    spread = max(0.0, heterogeneity)

    for i in range(hosts):
        agent_id = f"agent-{i:03d}"
        poisoned = i in poisoned_indexes
        if poisoned:
            poisoned_ids.add(agent_id)
        agents.append(
            Agent(
                agent_id=agent_id,
                risk_scale=min(1.30, max(0.70, rng.gauss(1.0, spread))),
                curiosity_scale=min(1.35, max(0.65, rng.gauss(1.0, spread))),
                investigation_bias=rng.uniform(-0.04, 0.04) * min(spread / 0.12, 1.5),
                report_inversion=poisoned,
            )
        )
    return agents, poisoned_ids


def _trust_gap(collective: CollectiveMemory, poisoned_ids: set[str]) -> float:
    honest = [state.score for source, state in collective.source_trust.items() if source not in poisoned_ids]
    poisoned = [state.score for source, state in collective.source_trust.items() if source in poisoned_ids]
    if not honest or not poisoned:
        return 0.0
    return sum(honest) / len(honest) - sum(poisoned) / len(poisoned)


def _snapshot(
    *,
    step: int,
    total_steps: int,
    evaluator: Evaluator,
    agents: list[Agent],
    collective: CollectiveMemory,
    poisoned_ids: set[str],
) -> SimulationSnapshot:
    investigated = sum(a.investigated for a in agents)
    return SimulationSnapshot(
        step=step,
        total_steps=total_steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positives=evaluator.true_positives,
        false_positives=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        detection_rate=evaluator.true_positives / max(evaluator.pathogen_events, 1),
        precision=evaluator.true_positives / max(investigated, 1),
        false_positive_rate=evaluator.false_positives / max(evaluator.benign_events, 1),
        collective_patterns=len(collective.patterns),
        open_questions=len(collective.open_questions()),
        forgotten_episodes=sum(a.memory.forgotten for a in agents),
        consolidated_episodes=sum(a.memory.consolidated for a in agents),
        mean_source_trust=collective.mean_source_trust,
        low_trust_sources=collective.low_trust_sources(),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(collective, poisoned_ids),
    )


def run_simulation(
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    on_snapshot: Callable[[SimulationSnapshot], None] | None = None,
) -> tuple[SimulationResult, CollectiveMemory]:
    rng = random.Random(seed)
    profiles = make_profiles(hosts, rng)
    agents, poisoned_ids = _make_agents(hosts, rng, poison_fraction, heterogeneity)
    collective = CollectiveMemory()
    evaluator = Evaluator()

    for step in range(steps):
        for profile, agent in zip(profiles, agents):
            inject = step >= 50 and rng.random() < threat_rate
            if inject:
                roll = rng.random()
                if roll < 0.40:
                    kind = "ransom_sim"
                elif roll < 0.72:
                    kind = "bot_sim"
                else:
                    kind = "stealth_sim"
                event = pathogen_event(kind, profile, rng)
            else:
                event = benign_event(profile, rng)

            assessment = agent.observe(step, event.observation, collective)
            evaluator.record(
                is_threat=event.is_threat,
                investigated=assessment.should_investigate,
            )

        collective.recalibrate_sources()
        if on_snapshot is not None:
            on_snapshot(
                _snapshot(
                    step=step + 1,
                    total_steps=steps,
                    evaluator=evaluator,
                    agents=agents,
                    collective=collective,
                    poisoned_ids=poisoned_ids,
                )
            )

    investigated = sum(a.investigated for a in agents)
    result = SimulationResult(
        hosts=hosts,
        steps=steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positive_investigations=evaluator.true_positives,
        false_positive_investigations=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        collective_patterns=len(collective.patterns),
        open_questions=len(collective.open_questions()),
        forgotten_episodes=sum(a.memory.forgotten for a in agents),
        consolidated_episodes=sum(a.memory.consolidated for a in agents),
        mean_source_trust=collective.mean_source_trust,
        low_trust_sources=collective.low_trust_sources(),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(collective, poisoned_ids),
    )
    return result, collective
