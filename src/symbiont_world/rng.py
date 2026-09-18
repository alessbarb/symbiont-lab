"""Deterministic, namespaced RNG streams for the world kernel.

Mirrors the derivation scheme of symbiont.environment.rng.derive_seed
(sha256 of "<prefix>:<seed>:<namespace>") without importing it, per
docs/design/symbiont-world-v1.md §2: symbiont_world imports nothing.
Independent namespacing keeps world randomness from perturbing the
existing same-seed reproducibility of synthetic experiments (§3, inv. 2).
"""
from __future__ import annotations

from hashlib import sha256
import random


def derive_world_seed(seed: int, namespace: str) -> int:
    payload = f"symbiont-world:{int(seed)}:{namespace}".encode("utf-8")
    return int.from_bytes(sha256(payload).digest()[:16], "big")


def derive_world_rng(seed: int, namespace: str) -> random.Random:
    return random.Random(derive_world_seed(seed, namespace))
