from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Iterable

FEATURES = (
    "cpu",
    "network",
    "file_changes",
    "new_processes",
    "persistence_changes",
)


@dataclass(slots=True, frozen=True)
class Observation:
    """What an agent can perceive. Ground truth intentionally lives elsewhere."""

    cpu: float
    network: float
    file_changes: float
    new_processes: float
    persistence_changes: float

    def vector(self) -> tuple[float, ...]:
        return tuple(float(getattr(self, name)) for name in FEATURES)


@dataclass(slots=True)
class RunningStat:
    """Online statistic with slow forgetting so the host model can adapt."""

    n: int = 0
    mean: float = 0.0
    variance_estimate: float = 0.0
    alpha: float = 0.06

    def update(self, x: float) -> None:
        self.n += 1
        if self.n == 1:
            self.mean = x
            self.variance_estimate = 0.0
            return
        delta = x - self.mean
        self.mean += self.alpha * delta
        self.variance_estimate = (
            (1.0 - self.alpha) * self.variance_estimate
            + self.alpha * delta * delta
        )

    @property
    def variance(self) -> float:
        return max(self.variance_estimate, 1e-6)

    @property
    def std(self) -> float:
        return sqrt(self.variance)


@dataclass(slots=True)
class HostModel:
    stats: dict[str, RunningStat] = field(
        default_factory=lambda: {name: RunningStat() for name in FEATURES}
    )

    def update(self, obs: Observation) -> None:
        for name, value in zip(FEATURES, obs.vector()):
            self.stats[name].update(value)

    @property
    def samples(self) -> int:
        return min(stat.n for stat in self.stats.values())

    @property
    def maturity(self) -> float:
        return min(self.samples / 24.0, 1.0)

    def novelty(self, obs: Observation) -> float:
        if self.maturity < 0.25:
            return 0.0
        z_scores = []
        for name, value in zip(FEATURES, obs.vector()):
            stat = self.stats[name]
            z_scores.append(abs(value - stat.mean) / max(stat.std, 0.12))
        avg_z = sum(min(z, 8.0) for z in z_scores) / len(z_scores)
        return min(avg_z / 4.0, 1.0)


@dataclass(slots=True, frozen=True)
class Assessment:
    novelty: float
    uncertainty: float
    relevance: float
    information_gain: float
    curiosity: float
    risk: float
    collective_threat: float
    collective_certainty: float
    fingerprint: str
    should_investigate: bool
    believes_threat: bool
    threat_probability: float | None = None


def fingerprint(obs: Observation) -> str:
    """Abstract behavior into a coarse signature; no host/user identifiers."""
    bins: list[str] = []
    for value in obs.vector():
        if value < 0.25:
            bins.append("L")
        elif value < 0.60:
            bins.append("M")
        else:
            bins.append("H")
    return "-".join(bins)


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
