from __future__ import annotations

from dataclasses import dataclass
import random

from symbiont.core.foundation.model import Observation
from .regimes import apply_regime_shift


@dataclass(slots=True)
class HostProfile:
    cpu: float
    network: float
    file_changes: float
    new_processes: float
    persistence_changes: float


@dataclass(slots=True, frozen=True)
class SimulatedEvent:
    """Simulator-only envelope. Agents receive only ``observation``."""

    observation: Observation
    truth_label: str
    is_threat: bool


def make_profiles(n: int, rng: random.Random) -> list[HostProfile]:
    return [
        HostProfile(
            cpu=rng.uniform(0.08, 0.35),
            network=rng.uniform(0.05, 0.30),
            file_changes=rng.uniform(0.03, 0.18),
            new_processes=rng.uniform(0.02, 0.16),
            persistence_changes=rng.uniform(0.00, 0.05),
        )
        for _ in range(n)
    ]


def _jitter(base: float, rng: random.Random, scale: float = 0.08) -> float:
    return min(1.0, max(0.0, rng.gauss(base, scale)))


def benign_event(profile: HostProfile, rng: random.Random) -> SimulatedEvent:
    roll = rng.random()
    if roll < 0.025:
        obs = Observation(
            cpu=_jitter(profile.cpu + 0.18, rng),
            network=_jitter(profile.network + 0.20, rng),
            file_changes=_jitter(profile.file_changes + 0.28, rng),
            new_processes=_jitter(profile.new_processes + 0.20, rng),
            persistence_changes=_jitter(profile.persistence_changes + 0.10, rng),
        )
        return SimulatedEvent(obs, "benign:update", False)
    if roll < 0.040:
        obs = Observation(
            cpu=_jitter(profile.cpu + 0.14, rng),
            network=_jitter(profile.network + 0.08, rng),
            file_changes=rng.uniform(0.48, 0.78),
            new_processes=_jitter(profile.new_processes + 0.10, rng),
            persistence_changes=_jitter(profile.persistence_changes + 0.03, rng, 0.03),
        )
        return SimulatedEvent(obs, "benign:backup", False)
    if roll < 0.052:
        obs = Observation(
            cpu=rng.uniform(0.45, 0.78),
            network=_jitter(profile.network + 0.18, rng),
            file_changes=rng.uniform(0.30, 0.62),
            new_processes=rng.uniform(0.32, 0.62),
            persistence_changes=_jitter(profile.persistence_changes + 0.08, rng, 0.04),
        )
        return SimulatedEvent(obs, "benign:build", False)

    obs = Observation(
        cpu=_jitter(profile.cpu, rng),
        network=_jitter(profile.network, rng),
        file_changes=_jitter(profile.file_changes, rng),
        new_processes=_jitter(profile.new_processes, rng),
        persistence_changes=_jitter(profile.persistence_changes, rng, 0.025),
    )
    return SimulatedEvent(obs, "benign:normal", False)


def pathogen_event(kind: str, profile: HostProfile, rng: random.Random) -> SimulatedEvent:
    if kind == "ransom_sim":
        obs = Observation(
            cpu=_jitter(profile.cpu + 0.18, rng),
            network=_jitter(profile.network + 0.06, rng),
            file_changes=rng.uniform(0.58, 0.90),
            new_processes=rng.uniform(0.25, 0.58),
            persistence_changes=rng.uniform(0.18, 0.48),
        )
    elif kind == "bot_sim":
        obs = Observation(
            cpu=rng.uniform(0.32, 0.65),
            network=rng.uniform(0.58, 0.90),
            file_changes=rng.uniform(0.05, 0.28),
            new_processes=rng.uniform(0.22, 0.55),
            persistence_changes=rng.uniform(0.28, 0.62),
        )
    elif kind == "stealth_sim":
        obs = Observation(
            cpu=_jitter(profile.cpu + 0.08, rng, 0.05),
            network=_jitter(profile.network + 0.13, rng, 0.06),
            file_changes=_jitter(profile.file_changes + 0.10, rng, 0.05),
            new_processes=_jitter(profile.new_processes + 0.12, rng, 0.05),
            persistence_changes=_jitter(profile.persistence_changes + 0.12, rng, 0.04),
        )
    else:
        raise ValueError(f"unknown pathogen kind: {kind}")
    return SimulatedEvent(obs, f"pathogen:{kind}", True)
