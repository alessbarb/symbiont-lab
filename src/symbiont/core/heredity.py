"""Closed, bounded heritable loci layered over validated genomes (v0.67)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


_ALLOWED_LOCI = frozenset({
    "initial_concepts", "soft_node_budget", "soft_edge_budget",
    "learning_rate", "forgetting_rate", "behavior_exploration",
})


@dataclass(frozen=True, slots=True)
class HeritableGenome:
    genome_id: str
    loci: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.loci]
        if len(keys) != len(set(keys)) or any(key not in _ALLOWED_LOCI for key in keys):
            raise ValueError("unknown or duplicate heritable locus")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for _, value in self.loci):
            raise ValueError("locus values must be numeric")

    @property
    def identity(self) -> str:
        payload = json.dumps({"genome_id": self.genome_id, "loci": self.loci}, separators=(",", ":"), sort_keys=True)
        return "genome_" + sha256(payload.encode()).hexdigest()[:16]


def recombine_loci(parent_a: HeritableGenome, parent_b: HeritableGenome, *, choose_a: bool = True) -> HeritableGenome:
    """Deterministically select declared loci; no permissions or kernel limits can be loci."""
    a, b = dict(parent_a.loci), dict(parent_b.loci)
    keys = sorted(set(a) | set(b))
    loci = tuple((key, (a if choose_a else b).get(key, (b if choose_a else a).get(key))) for key in keys)
    return HeritableGenome(genome_id=f"{parent_a.genome_id}+{parent_b.genome_id}", loci=loci)


__all__ = ["HeritableGenome", "recombine_loci"]
