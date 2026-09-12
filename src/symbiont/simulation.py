from __future__ import annotations

from dataclasses import dataclass
import random

from .agent import Agent
from .collective import CollectiveMemory
from .world import make_profiles, normal_observation, pathogen_observation


@dataclass(slots=True)
class SimulationResult:
    hosts: int
    steps: int
    pathogen_events: int
    investigated: int
    true_positive_investigations: int
    false_positive_investigations: int
    collective_patterns: int
    open_questions: int

    @property
    def detection_rate(self) -> float:
        return self.true_positive_investigations / max(self.pathogen_events, 1)

    @property
    def precision(self) -> float:
        return self.true_positive_investigations / max(self.investigated, 1)


def run_simulation(hosts: int = 100, steps: int = 300, seed: int = 7) -> tuple[SimulationResult, CollectiveMemory]:
    rng = random.Random(seed)
    profiles = make_profiles(hosts, rng)
    agents = [Agent(f"agent-{i:03d}") for i in range(hosts)]
    collective = CollectiveMemory()
    pathogen_events = 0

    for step in range(steps):
        for idx, (profile, agent) in enumerate(zip(profiles, agents)):
            # Quiet baseline first; simulated pathogens appear after learning has matured.
            inject = step >= 50 and rng.random() < 0.018
            if inject:
                kind = "ransom_sim" if rng.random() < 0.55 else "bot_sim"
                obs = pathogen_observation(kind, profile, rng)
                pathogen_events += 1
            else:
                obs = normal_observation(profile, rng)
            agent.observe(step, obs, collective)

    investigated = sum(a.investigated for a in agents)
    tp = sum(a.true_positive_investigations for a in agents)
    fp = sum(a.false_positive_investigations for a in agents)
    result = SimulationResult(
        hosts=hosts,
        steps=steps,
        pathogen_events=pathogen_events,
        investigated=investigated,
        true_positive_investigations=tp,
        false_positive_investigations=fp,
        collective_patterns=len(collective.patterns),
        open_questions=len(collective.open_questions()),
    )
    return result, collective
