"""Evaluator-only runtime social interaction loop.

Each runtime selects from its own opaque presence and relation memory. The
harness does not assign roles, valence labels or a target pair; it only supplies
the authorized habitat and a bounded exchange opportunity.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeEmergenceStudy:
    ticks: int
    interactions: int
    unique_pairs: int
    pair_entropy: float
    isolated_members: int
    reciprocal_observations: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_emergence_study(
    *, ticks: int = 12, members: int = 4
) -> SocialRuntimeEmergenceStudy:
    if ticks < 1 or members < 2:
        raise ValueError("invalid runtime emergence parameters")
    ids = tuple(f"runtime-{index}" for index in range(members))
    habitat = SocialHabitat(
        EcologicalResourcePool({"food": float(ticks * members)}), max_members=members
    )
    for organism_id in ids:
        habitat.admit(organism_id)
    runtimes: tuple[OrganismRuntime, ...] = tuple(
        OrganismRuntime(organism_id=organism_id, social_habitat=habitat) for organism_id in ids
    )
    pairs: Counter[tuple[str, str]] = Counter()
    touched: set[str] = set()
    for _ in range(ticks):
        for runtime in runtimes:
            outcome = runtime.autonomous_social_step()
            if outcome is None or outcome.granted <= 0.0:
                runtime.tick()
                continue
            touched.update((runtime.organism_id, outcome.target_id))
            pairs[tuple(sorted((runtime.organism_id, outcome.target_id)))] += 1
            runtime.tick()
    interactions = sum(pairs.values())
    entropy = 0.0
    if interactions:
        entropy = -sum(
            (count / interactions) * math.log(count / interactions) for count in pairs.values()
        )
    return SocialRuntimeEmergenceStudy(
        ticks=ticks,
        interactions=interactions,
        unique_pairs=len(pairs),
        pair_entropy=entropy,
        isolated_members=len(set(ids) - touched),
        reciprocal_observations=sum(
            r.reciprocal_observations for r in habitat.engine.ledger.relations
        ),
    )


__all__ = ["SocialRuntimeEmergenceStudy", "run_social_runtime_emergence_study"]
