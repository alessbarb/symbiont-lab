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
class RNGStreams:
    profiles: random.Random
    agents: random.Random
    reporters: random.Random
    schedule: random.Random
    observations: random.Random
    drift: random.Random


def make_rng_streams(seed: int) -> RNGStreams:
    return RNGStreams(
        profiles=random.Random(derive_seed(seed, "profiles")),
        agents=random.Random(derive_seed(seed, "agents")),
        reporters=random.Random(derive_seed(seed, "reporters")),
        schedule=random.Random(derive_seed(seed, "schedule")),
        observations=random.Random(derive_seed(seed, "observations")),
        drift=random.Random(derive_seed(seed, "drift")),
    )
