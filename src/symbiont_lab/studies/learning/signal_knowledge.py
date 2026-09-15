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


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    """Evaluator-only summary for one synthetic environment."""

    name: str
    seed: int
    ticks: int
    profiles: int
    supported: int
    contested: int
    coverage: float

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    """Aggregate evaluator metrics for the frozen acceptance matrix.

    The ``lag`` scenario is the only scenario labelled as an expected
    positive.  This label is retained in ``symbiont_lab`` and is never passed
    to the core engine.
    """

    total_scenarios: int
    supported_scenarios: int
    expected_positive_scenarios: int
    true_positive_scenarios: int
    false_positive_scenarios: int
    support_precision: float
    lag_recall: float
    mean_coverage: float

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


def run_acceptance_scenarios(seed: int, *, ticks: int = 256) -> tuple[ScenarioOutcome, ...]:
    """Run the bounded evaluator matrix with opaque inputs only.

    The generator retains the scenario truth locally in ``symbiont_lab``;
    the core engine receives only tokenized observations and candidate pairs.
    """
    if ticks < 192:
        raise ValueError("acceptance scenarios require at least 192 ticks")
    identity = SignalIdentity(bytes(range(32)))
    names = ("constant", "positive_ar", "negative_ar", "lag", "common_source", "gaps", "id_change")
    outcomes: list[ScenarioOutcome] = []
    for index, name in enumerate(names):
        rng = random.Random(seed + index * 1009)
        engine = SignalKnowledgeEngine()
        a, b = identity.signal_id(f"scenario.{name}.a"), identity.signal_id(f"scenario.{name}.b")
        previous_a = previous_b = 0.0
        valid = 0
        for tick in range(1, ticks + 1):
            source = rng.gauss(0.0, 1.0)
            if name == "constant": target = 1.0
            elif name == "positive_ar": target = 0.8 * previous_b + 0.2 * source
            elif name == "negative_ar": target = -0.8 * previous_b + 0.2 * source
            elif name == "common_source": target = source + rng.gauss(0.0, 0.5)
            elif name == "lag": target = previous_a + rng.gauss(0.0, 0.02)
            else: target = 0.6 * source + 0.4 * previous_b + rng.gauss(0.0, 0.05)
            previous_a, previous_b = source, target
            sid_a = a
            if name == "id_change" and tick > ticks // 2:
                sid_a = identity.signal_id("scenario.id_change.a.v2")
            values = [SignalObservation(sid_a, True, True, source, "nominal")]
            if name != "gaps" or tick % 5:
                values.append(SignalObservation(b, True, True, target, "nominal"))
                valid += 1
            engine.observe(SignalObservationBatch(tick, tuple(values)), candidate_pairs=((sid_a, b),))
        claims = [c for p in engine.view() for c in p["claims"]]
        outcomes.append(ScenarioOutcome(name, seed, ticks, len(engine.view()),
                                        sum(c["status"] == "supported" for c in claims),
                                        sum(c["status"] == "contested" for c in claims),
                                        valid / ticks))
    return tuple(outcomes)


def run_acceptance_suite(*, seeds: tuple[int, ...] = (101, 127, 149), ticks: int = 256) -> tuple[ScenarioOutcome, ...]:
    """Run the frozen acceptance seeds without calibrating on their results."""
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be non-empty integer tuple")
    return tuple(item for seed in seeds for item in run_acceptance_scenarios(seed, ticks=ticks))


def summarize_acceptance(results: tuple[ScenarioOutcome, ...]) -> AcceptanceReport:
    """Summarize outcomes without changing engine decisions or labels."""
    if not results:
        raise ValueError("results must be non-empty")
    supported = sum(item.supported > 0 for item in results)
    expected = sum(item.name == "lag" for item in results)
    true_positive = sum(item.name == "lag" and item.supported > 0 for item in results)
    false_positive = supported - true_positive
    precision = true_positive / supported if supported else 0.0
    recall = true_positive / expected if expected else 0.0
    return AcceptanceReport(
        total_scenarios=len(results),
        supported_scenarios=supported,
        expected_positive_scenarios=expected,
        true_positive_scenarios=true_positive,
        false_positive_scenarios=false_positive,
        support_precision=precision,
        lag_recall=recall,
        mean_coverage=sum(item.coverage for item in results) / len(results),
    )


__all__ = ["SignalKnowledgeOutcome", "ScenarioOutcome", "AcceptanceReport", "run_signal_knowledge", "run_acceptance_scenarios", "run_acceptance_suite", "summarize_acceptance"]
