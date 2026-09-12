from __future__ import annotations

from dataclasses import dataclass
import random

from .model import Observation


@dataclass(slots=True)
class HostProfile:
    cpu: float
    network: float
    file_changes: float
    new_processes: float
    persistence_changes: float


def make_profiles(n: int, rng: random.Random) -> list[HostProfile]:
    profiles = []
    for _ in range(n):
        profiles.append(
            HostProfile(
                cpu=rng.uniform(0.08, 0.35),
                network=rng.uniform(0.05, 0.30),
                file_changes=rng.uniform(0.03, 0.18),
                new_processes=rng.uniform(0.02, 0.16),
                persistence_changes=rng.uniform(0.00, 0.05),
            )
        )
    return profiles


def _jitter(base: float, rng: random.Random, scale: float = 0.08) -> float:
    return min(1.0, max(0.0, rng.gauss(base, scale)))


def normal_observation(profile: HostProfile, rng: random.Random) -> Observation:
    # A benign software update occasionally looks interesting but should become familiar.
    if rng.random() < 0.025:
        return Observation(
            cpu=_jitter(profile.cpu + 0.18, rng),
            network=_jitter(profile.network + 0.20, rng),
            file_changes=_jitter(profile.file_changes + 0.28, rng),
            new_processes=_jitter(profile.new_processes + 0.20, rng),
            persistence_changes=_jitter(profile.persistence_changes + 0.10, rng),
            label="benign_update",
        )
    return Observation(
        cpu=_jitter(profile.cpu, rng),
        network=_jitter(profile.network, rng),
        file_changes=_jitter(profile.file_changes, rng),
        new_processes=_jitter(profile.new_processes, rng),
        persistence_changes=_jitter(profile.persistence_changes, rng, 0.025),
        label="normal",
    )


def pathogen_observation(kind: str, profile: HostProfile, rng: random.Random) -> Observation:
    if kind == "ransom_sim":
        return Observation(
            cpu=_jitter(profile.cpu + 0.25, rng),
            network=_jitter(profile.network + 0.08, rng),
            file_changes=rng.uniform(0.78, 1.0),
            new_processes=rng.uniform(0.35, 0.75),
            persistence_changes=rng.uniform(0.30, 0.70),
            label="pathogen:ransom_sim",
        )
    if kind == "bot_sim":
        return Observation(
            cpu=rng.uniform(0.45, 0.80),
            network=rng.uniform(0.75, 1.0),
            file_changes=rng.uniform(0.05, 0.25),
            new_processes=rng.uniform(0.35, 0.70),
            persistence_changes=rng.uniform(0.45, 0.85),
            label="pathogen:bot_sim",
        )
    raise ValueError(f"unknown pathogen kind: {kind}")
