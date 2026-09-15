"""Reproducible evaluator-side study for the opaque signal engine.

Truth and labels live here, never in :mod:`symbiont.core`.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import random

from symbiont.core.signal_identity import SignalIdentity
from symbiont.core.signal_knowledge import SignalKnowledgeEngine
from symbiont.core.signal_knowledge_types import SignalObservation, SignalObservationBatch


@dataclass(frozen=True, slots=True)
class SignalKnowledgeOutcome:
    seed: int
    ticks: int
    profiles: int
    claims: int
    supported: int

    def as_dict(self):
        return asdict(self)


def run_signal_knowledge(seed: int, *, ticks: int = 192) -> SignalKnowledgeOutcome:
    if ticks < 1:
        raise ValueError("ticks must be positive")
    rng = random.Random(seed)
    identity = SignalIdentity(bytes(range(32)))
    a, b = identity.signal_id("fixture.a"), identity.signal_id("fixture.b")
    engine = SignalKnowledgeEngine()
    previous_b = 0.0
    for tick in range(1, ticks + 1):
        value_a = rng.gauss(0.0, 1.0)
        value_b = 0.7 * value_a + 0.3 * previous_b + rng.gauss(0.0, 0.05)
        previous_b = value_b
        engine.observe(SignalObservationBatch(tick, (
            SignalObservation(a, True, True, value_a, "nominal"),
            SignalObservation(b, True, True, value_b, "nominal"),
        )), candidate_pairs=((a, b),))
    view = engine.view()
    claims = [claim for profile in view for claim in profile["claims"]]
    return SignalKnowledgeOutcome(seed, ticks, len(view), len(claims), sum(c["status"] == "supported" for c in claims))


__all__ = ["SignalKnowledgeOutcome", "run_signal_knowledge"]
