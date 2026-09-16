"""Evaluator-only prolonged runtime ecology study."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeLongitudinalStudy:
    ticks: int
    members: int
    interactions: int
    unique_pairs: int
    pair_entropy: float
    checkpoint_replay_equal: bool
    isolated_members: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_longitudinal_study(*, ticks: int = 48, members: int = 4) -> SocialRuntimeLongitudinalStudy:
    """Run autonomous social steps long enough to test persistence and replay.

    The harness supplies only an authorized habitat and finite anonymous
    resources. It never selects a peer, assigns a role, or labels an outcome.
    """
    if ticks < 8 or members < 2:
        raise ValueError("ticks must be at least 8 and members at least 2")
    ids = tuple(f"resident-{index}" for index in range(members))
    habitat = SocialHabitat(EcologicalResourcePool({"food": float(ticks * members)}), max_members=members)
    for organism_id in ids:
        habitat.admit(organism_id)
    runtimes = [OrganismRuntime(organism_id=organism_id, social_habitat=habitat) for organism_id in ids]
    pairs: Counter[tuple[str, str]] = Counter()
    touched: set[str] = set()
    replay_equal = True
    for tick in range(ticks):
        if tick == ticks // 2:
            checkpoints = [runtime.checkpoint() for runtime in runtimes]
            restored = [OrganismRuntime.from_checkpoint(payload, social_habitat=habitat) for payload in checkpoints]
            replay_equal = all(
                left.social_ledger.checkpoint() == right.social_ledger.checkpoint()
                for left, right in zip(runtimes, restored)
            )
            runtimes = restored
        for runtime in runtimes:
            outcome = runtime.autonomous_social_step()
            if outcome is None or outcome.granted <= 0.0:
                continue
            touched.update((runtime.organism_id, outcome.target_id))
            pairs[tuple(sorted((runtime.organism_id, outcome.target_id)))] += 1
    interactions = sum(pairs.values())
    entropy = 0.0
    if interactions:
        entropy = -sum((count / interactions) * math.log(count / interactions) for count in pairs.values())
    return SocialRuntimeLongitudinalStudy(
        ticks=ticks, members=members, interactions=interactions,
        unique_pairs=len(pairs), pair_entropy=entropy,
        checkpoint_replay_equal=replay_equal,
        isolated_members=len(set(ids) - touched),
    )


__all__ = ["SocialRuntimeLongitudinalStudy", "run_social_runtime_longitudinal_study"]
