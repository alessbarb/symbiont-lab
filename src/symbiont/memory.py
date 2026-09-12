from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Episode:
    step: int
    fingerprint: str
    curiosity: float
    risk: float
    believed_threat: bool

    @property
    def salience(self) -> float:
        return max(self.curiosity, self.risk)


@dataclass(slots=True)
class SemanticMemory:
    encounters: int = 0
    threat_beliefs: int = 0
    salience_sum: float = 0.0

    def absorb(self, episode: Episode) -> None:
        self.encounters += 1
        self.threat_beliefs += int(episode.believed_threat)
        self.salience_sum += episode.salience

    @property
    def threat_rate(self) -> float:
        return self.threat_beliefs / max(self.encounters, 1)


@dataclass(slots=True)
class AgentMemory:
    """Bounded episodic memory plus compressed long-term concepts."""

    retention_steps: int = 90
    max_episodes: int = 128
    episodes: list[Episode] = field(default_factory=list)
    concepts: dict[str, SemanticMemory] = field(default_factory=dict)
    forgotten: int = 0
    consolidated: int = 0

    def remember(self, episode: Episode) -> None:
        self.episodes.append(episode)
        if len(self.episodes) > self.max_episodes:
            self._consolidate(self.episodes.pop(0))

    def forget(self, current_step: int) -> None:
        retained: list[Episode] = []
        for episode in self.episodes:
            age = current_step - episode.step
            if age <= self.retention_steps or episode.salience >= 0.72:
                retained.append(episode)
            elif episode.salience >= 0.24:
                self._consolidate(episode)
            else:
                self.forgotten += 1
        self.episodes = retained

    def _consolidate(self, episode: Episode) -> None:
        concept = self.concepts.setdefault(episode.fingerprint, SemanticMemory())
        concept.absorb(episode)
        self.consolidated += 1
