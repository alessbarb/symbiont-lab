from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import random


def derive_seed(seed: int, namespace: str) -> int:
    """Derive a stable namespace-specific seed from one experiment seed.

    The derivation is independent of Python's process hash randomization and keeps
    unrelated random mechanisms from perturbing each other. Paired experiments can
    therefore change reporter poisoning without silently changing host profiles,
    agent traits or the synthetic world.
    """
    payload = f"symbiont-lab:{int(seed)}:{namespace}".encode("utf-8")
    return int.from_bytes(sha256(payload).digest()[:16], "big")


@dataclass(slots=True)
class AgentRNG:
    """Compatibility facade with causally separated reporter and trait draws.

    `_make_agents` historically receives one RNG and uses `sample()` to select
    inverted reporters before drawing agent traits with `gauss()`/`uniform()`.
    Routing those operations to independent streams keeps that call contract while
    ensuring a poisoning intervention cannot shift the trait sequence.
    """

    traits: random.Random
    reporters: random.Random

    def sample(self, population, k: int):
        return self.reporters.sample(population, k)

    def gauss(self, mu: float, sigma: float) -> float:
        return self.traits.gauss(mu, sigma)

    def uniform(self, a: float, b: float) -> float:
        return self.traits.uniform(a, b)


@dataclass(slots=True)
class RNGStreams:
    profiles: random.Random
    agents: AgentRNG
    reporters: random.Random
    schedule: random.Random
    observations: random.Random
    drift: random.Random


def make_rng_streams(seed: int) -> RNGStreams:
    trait_rng = random.Random(derive_seed(seed, "agents"))
    reporter_rng = random.Random(derive_seed(seed, "reporters"))
    return RNGStreams(
        profiles=random.Random(derive_seed(seed, "profiles")),
        agents=AgentRNG(traits=trait_rng, reporters=reporter_rng),
        reporters=reporter_rng,
        schedule=random.Random(derive_seed(seed, "schedule")),
        observations=random.Random(derive_seed(seed, "observations")),
        drift=random.Random(derive_seed(seed, "drift")),
    )
