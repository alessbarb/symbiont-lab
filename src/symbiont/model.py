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
    cpu: float
    network: float
    file_changes: float
    new_processes: float
    persistence_changes: float
    label: str = "normal"

    def vector(self) -> tuple[float, ...]:
        return tuple(float(getattr(self, name)) for name in FEATURES)


@dataclass(slots=True)
class RunningStat:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)

    @property
    def variance(self) -> float:
        return self.m2 / max(self.n - 1, 1)

    @property
    def std(self) -> float:
        return sqrt(max(self.variance, 1e-6))


@dataclass(slots=True)
class HostModel:
    stats: dict[str, RunningStat] = field(
        default_factory=lambda: {name: RunningStat() for name in FEATURES}
    )

    def update(self, obs: Observation) -> None:
        for name, value in zip(FEATURES, obs.vector()):
            self.stats[name].update(value)

    @property
    def maturity(self) -> float:
        samples = min(stat.n for stat in self.stats.values())
        return min(samples / 20.0, 1.0)

    def novelty(self, obs: Observation) -> float:
        if self.maturity < 0.25:
            return 0.0
        z_scores = []
        for name, value in zip(FEATURES, obs.vector()):
            stat = self.stats[name]
            z_scores.append(abs(value - stat.mean) / max(stat.std, 0.15))
        # Saturating score: 0 is familiar; 1 is strongly outside the learned baseline.
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
    fingerprint: str
    should_investigate: bool


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
