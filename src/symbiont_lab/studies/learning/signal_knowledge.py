"""Reproducible evaluator-side study for the opaque signal engine.

Truth and labels live here, never in :mod:`symbiont.core`.
"""

from __future__ import annotations

import json
import random
import tracemalloc
from dataclasses import asdict, dataclass

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
    discovery_latency: int | None = None
    selected_observations: int = 0

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
    mean_discovery_latency: float | None
    total_selected_observations: int

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AcceptanceResourceReport:
    """Measured Python allocation and serialized evaluator-output size."""

    peak_tracemalloc_bytes: int
    result_json_bytes: int

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PressureReport:
    ticks: int
    profiles: int
    claims: int
    max_claims_per_signal: int
    knowledge_checkpoint_bytes: int = 0

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
        engine.observe(
            SignalObservationBatch(
                tick,
                (
                    SignalObservation(a, True, True, value_a, "nominal"),
                    SignalObservation(b, True, True, value_b, "nominal"),
                ),
            ),
            candidate_pairs=((a, b),),
        )
    view = engine.view()
    claims = [claim for profile in view for claim in profile["claims"]]
    return SignalKnowledgeOutcome(
        seed, ticks, len(view), len(claims), sum(c["status"] == "supported" for c in claims)
    )


def run_acceptance_scenarios(
    seed: int, *, ticks: int = 256, include_extended: bool = False
) -> tuple[ScenarioOutcome, ...]:
    """Run the bounded evaluator matrix with opaque inputs only.

    The generator retains the scenario truth locally in ``symbiont_lab``;
    the core engine receives only tokenized observations and candidate pairs.
    """
    if ticks < 192:
        raise ValueError("acceptance scenarios require at least 192 ticks")
    identity = SignalIdentity(bytes(range(32)))
    names = ("constant", "positive_ar", "negative_ar", "lag", "common_source", "gaps", "id_change")
    if include_extended:
        names += ("regime_change", "multiple_noise", "scale", "trend", "invalid_quality")
    outcomes: list[ScenarioOutcome] = []
    for index, name in enumerate(names):
        rng = random.Random(seed + index * 1009)
        engine = SignalKnowledgeEngine()
        a, b = identity.signal_id(f"scenario.{name}.a"), identity.signal_id(f"scenario.{name}.b")
        previous_a = previous_b = 0.0
        valid = 0
        first_support: int | None = None
        for tick in range(1, ticks + 1):
            source = rng.gauss(0.0, 1.0)
            if name == "constant":
                target = 1.0
            elif name == "positive_ar":
                target = 0.8 * previous_b + 0.2 * source
            elif name == "negative_ar":
                target = -0.8 * previous_b + 0.2 * source
            elif name == "common_source":
                target = source + rng.gauss(0.0, 0.5)
            elif name == "regime_change":
                target = (
                    (previous_a + rng.gauss(0.0, 0.05))
                    if tick <= ticks // 2
                    else rng.gauss(0.0, 1.0)
                )
            elif name == "multiple_noise":
                target = rng.gauss(0.0, 1.0)
            elif name == "scale":
                target = 100.0 * source + rng.gauss(0.0, 5.0)
            elif name == "trend":
                target = tick * 0.02 + rng.gauss(0.0, 0.2)
            elif name == "lag":
                target = previous_a + rng.gauss(0.0, 0.02)
            else:
                target = 0.6 * source + 0.4 * previous_b + rng.gauss(0.0, 0.05)
            previous_a, previous_b = source, target
            sid_a = a
            if name == "id_change" and tick > ticks // 2:
                sid_a = identity.signal_id("scenario.id_change.a.v2")
            values = [SignalObservation(sid_a, True, True, source, "nominal")]
            if name != "gaps" or tick % 5:
                quality = "degraded" if name == "invalid_quality" and tick % 7 == 0 else "nominal"
                values.append(SignalObservation(b, True, True, target, quality))
                valid += int(quality == "nominal")
            engine.observe(
                SignalObservationBatch(tick, tuple(values)), candidate_pairs=((sid_a, b),)
            )
            if any(c["status"] == "supported" for p in engine.view() for c in p["claims"]):
                if first_support is None:
                    first_support = tick
        claims = [c for p in engine.view() for c in p["claims"]]
        outcomes.append(
            ScenarioOutcome(
                name,
                seed,
                ticks,
                len(engine.view()),
                sum(c["status"] == "supported" for c in claims),
                sum(c["status"] == "contested" for c in claims),
                valid / ticks,
                first_support,
                valid,
            )
        )
    return tuple(outcomes)


def run_acceptance_suite(
    *, seeds: tuple[int, ...] = (101, 127, 149), ticks: int = 256
) -> tuple[ScenarioOutcome, ...]:
    """Run the frozen acceptance seeds without calibrating on their results."""
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be non-empty integer tuple")
    return tuple(item for seed in seeds for item in run_acceptance_scenarios(seed, ticks=ticks))


def run_full_acceptance_suite(
    *, seeds: tuple[int, ...] = (101, 127, 149), ticks: int = 256
) -> tuple[ScenarioOutcome, ...]:
    """Run baseline and extended §10 environments for each frozen seed."""
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be non-empty integer tuple")
    return tuple(
        item
        for seed in seeds
        for item in run_acceptance_scenarios(seed, ticks=ticks, include_extended=True)
    )


def run_signal_pressure(*, seed: int = 101, ticks: int = 256) -> PressureReport:
    """Exercise the hard profile/claim caps with 64 opaque signals."""
    if ticks < 1 or isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed and ticks must be valid")
    identity = SignalIdentity(bytes(range(32)))
    signal_ids = tuple(identity.signal_id(f"pressure.{i}") for i in range(64))
    rng = random.Random(seed)
    engine = SignalKnowledgeEngine()
    for tick in range(1, ticks + 1):
        observations = tuple(
            SignalObservation(sid, True, True, rng.gauss(0.0, 1.0), "nominal") for sid in signal_ids
        )
        engine.observe(
            SignalObservationBatch(tick, observations),
            candidate_pairs=tuple((signal_ids[i], signal_ids[(i + 1) % 64]) for i in range(64)),
        )
    view = engine.view()
    checkpoint = json.dumps(
        engine.checkpoint(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return PressureReport(
        ticks,
        len(view),
        sum(len(item["claims"]) for item in view),
        max((len(item["claims"]) for item in view), default=0),
        len(checkpoint),
    )


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
    latencies = [item.discovery_latency for item in results if item.discovery_latency is not None]
    return AcceptanceReport(
        total_scenarios=len(results),
        supported_scenarios=supported,
        expected_positive_scenarios=expected,
        true_positive_scenarios=true_positive,
        false_positive_scenarios=false_positive,
        support_precision=precision,
        lag_recall=recall,
        mean_coverage=sum(item.coverage for item in results) / len(results),
        mean_discovery_latency=sum(latencies) / len(latencies) if latencies else None,
        total_selected_observations=sum(item.selected_observations for item in results),
    )


def measure_acceptance_resources(
    *, seeds: tuple[int, ...] = (101, 127, 149), ticks: int = 256
) -> AcceptanceResourceReport:
    """Measure the suite without feeding measurements back into the engine.

    This deliberately reports Python allocations and evaluator JSON only; it
    is not a claim about whole-host RSS or journal retention.
    """
    tracemalloc.start()
    try:
        results = run_acceptance_suite(seeds=seeds, ticks=ticks)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    encoded = json.dumps(
        [item.as_dict() for item in results], sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return AcceptanceResourceReport(peak, len(encoded))


__all__ = [
    "SignalKnowledgeOutcome",
    "ScenarioOutcome",
    "AcceptanceReport",
    "AcceptanceResourceReport",
    "PressureReport",
    "run_signal_knowledge",
    "run_acceptance_scenarios",
    "run_acceptance_suite",
    "run_full_acceptance_suite",
    "run_signal_pressure",
    "summarize_acceptance",
    "measure_acceptance_resources",
]
