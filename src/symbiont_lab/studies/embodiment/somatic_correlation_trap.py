"""E5 adversarial falsification study: somatic-correlation trap.

Preregistered in:
research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md

This study attacks the current InferredBodySchema rule that may promote a
low-controllability input to somatic membership when it is strongly correlated
with a self-caused input. Evaluator truth remains exclusively in symbiont_lab.

A genuine somatic-correlated channel and a matched external-correlated channel
are deliberately made statistically similar. If both are assimilated into
internal_channels, the current mechanism does not have enough evidence to
distinguish bodily correlation from environmental correlation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel, InferredBodySchema, PerceptualStructure

_STUDY_ID = "embodiment.somatic-correlation-trap"
MAX_EXTERNAL_ASSIMILATION_RATE = 0.10
MIN_TRUE_SOMATIC_RATE = 0.70


@dataclass(frozen=True, slots=True)
class SomaticTrapSeedResult:
    seed: int
    self_caused_detected: bool
    true_somatic_detected: bool
    external_correlated_assimilated: bool
    external_independent_assimilated: bool
    self_controllability: float
    true_somatic_controllability: float
    external_correlated_controllability: float
    true_somatic_correlation: float
    external_correlated_correlation: float
    body_schema_confidence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SomaticCorrelationTrapStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[SomaticTrapSeedResult, ...]
    true_somatic_rate: float
    external_assimilation_rate: float
    independent_assimilation_rate: float
    e5_true_somatic_gate: bool
    e5_external_rejection_gate: bool
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [item.as_dict() for item in self.per_seed],
            "true_somatic_rate": self.true_somatic_rate,
            "external_assimilation_rate": self.external_assimilation_rate,
            "independent_assimilation_rate": self.independent_assimilation_rate,
            "e5_true_somatic_gate": self.e5_true_somatic_gate,
            "e5_external_rejection_gate": self.e5_external_rejection_gate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    result = tuple(seeds)
    if not result or len(result) > 64:
        raise ValueError("seeds must contain between 1 and 64 entries")
    if len(set(result)) != len(result):
        raise ValueError("seeds must be unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _run_seed(seed: int, *, steps: int) -> SomaticTrapSeedResult:
    rng = random.Random(seed)
    perceptual = PerceptualStructure()
    agency = AgencyModel()
    schema = InferredBodySchema()

    self_value = 0.0
    somatic_value = 0.0
    external_corr_value = 0.0
    external_indep_value = 0.0

    for _ in range(steps):
        active = rng.random() >= 0.30
        act = rng.uniform(0.25, 1.0) if active else 0.0

        # The genuinely self-caused input changes directly with activation.
        self_delta = 0.40 * act + rng.gauss(0.0, 0.015)
        self_value = _clip(self_value * 0.65 + self_delta)

        # Genuine somatic signal: not directly controlled, but tightly coupled
        # to the self-caused bodily state through shared physical state.
        somatic_target = 0.82 * self_value + rng.gauss(0.0, 0.02)
        somatic_delta = somatic_target - somatic_value
        somatic_value = _clip(somatic_target)

        # External trap: apparatus/world process tracks the same self-caused
        # observable just as tightly, despite not belonging to Body.
        external_target = 0.82 * self_value + rng.gauss(0.0, 0.02)
        external_corr_delta = external_target - external_corr_value
        external_corr_value = _clip(external_target)

        # Negative control: matched bounded external variation without coupling.
        independent_target = 0.75 * external_indep_value + rng.uniform(-0.12, 0.12)
        independent_delta = independent_target - external_indep_value
        external_indep_value = _clip(independent_target)

        inputs = {
            "in.self": self_value,
            "in.somatic": somatic_value,
            "in.external_corr": external_corr_value,
            "in.external_indep": external_indep_value,
        }
        deltas = {
            "in.self": self_delta,
            "in.somatic": somatic_delta,
            "in.external_corr": external_corr_delta,
            "in.external_indep": independent_delta,
        }
        perceptual.observe(inputs)
        agency.record_step({"out.0": act}, deltas)

    schema.update_from_agency(agency, perceptual)

    self_caused = "in.self" in schema.self_caused_channels
    true_somatic = "in.somatic" in schema.somatic_correlated_channels
    external_corr = "in.external_corr" in schema.internal_channels
    external_indep = "in.external_indep" in schema.internal_channels

    return SomaticTrapSeedResult(
        seed=seed,
        self_caused_detected=self_caused,
        true_somatic_detected=true_somatic,
        external_correlated_assimilated=external_corr,
        external_independent_assimilated=external_indep,
        self_controllability=float(agency.controllability.get("in.self", 0.0)),
        true_somatic_controllability=float(agency.controllability.get("in.somatic", 0.0)),
        external_correlated_controllability=float(agency.controllability.get("in.external_corr", 0.0)),
        true_somatic_correlation=float(perceptual.correlation("in.somatic", "in.self")),
        external_correlated_correlation=float(perceptual.correlation("in.external_corr", "in.self")),
        body_schema_confidence=float(schema.overall_confidence),
    )


def run_somatic_correlation_trap_study(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
    steps: int = 600,
) -> SomaticCorrelationTrapStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 50 or steps > 100_000:
        raise ValueError("steps must be within [50, 100000]")

    results = tuple(_run_seed(seed, steps=steps) for seed in normalized)
    replay = tuple(_run_seed(seed, steps=steps) for seed in normalized)

    true_rate = sum(item.true_somatic_detected for item in results) / len(results)
    external_rate = sum(item.external_correlated_assimilated for item in results) / len(results)
    independent_rate = sum(item.external_independent_assimilated for item in results) / len(results)

    true_gate = true_rate >= MIN_TRUE_SOMATIC_RATE
    external_gate = external_rate <= MAX_EXTERNAL_ASSIMILATION_RATE
    replay_deterministic = results == replay

    return SomaticCorrelationTrapStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        true_somatic_rate=true_rate,
        external_assimilation_rate=external_rate,
        independent_assimilation_rate=independent_rate,
        e5_true_somatic_gate=true_gate,
        e5_external_rejection_gate=external_gate,
        replay_deterministic=replay_deterministic,
        h1_supported=true_gate and external_gate and replay_deterministic,
    )


__all__ = [
    "SomaticTrapSeedResult",
    "SomaticCorrelationTrapStudy",
    "run_somatic_correlation_trap_study",
]
