"""E1 adversarial falsification study: yoked external causation.

Preregistered in:
research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md

This is a mechanism-level assay of AgencyModel. It deliberately does not modify
Symbiont or tune thresholds to obtain a positive result. Evaluator truth remains
entirely in symbiont_lab.

The study presents AgencyModel with:
- a genuinely activation-dependent channel,
- an externally yoked channel with matched activation correlation,
- an anti-causal control driven by the next activation,
- an independent matched-scale control.

If the yoked external channel is promoted as agentic at rates comparable to the
genuine channel, that is evidence for the preregistered H0 heuristic-contingency
account under this assay. The study reports that result rather than repairing it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel

_STUDY_ID = "embodiment.yoked-external-causation"
AGENCY_THRESHOLD = 0.5
MAX_FALSE_POSITIVE_RATE = 0.10
MIN_TRUE_POSITIVE_RATE = 0.70


@dataclass(frozen=True, slots=True)
class YokedCausationSeedResult:
    seed: int
    genuine_confidence: float
    yoked_confidence: float
    anticausal_confidence: float
    independent_confidence: float
    genuine_agentic: bool
    yoked_agentic: bool
    anticausal_agentic: bool
    independent_agentic: bool
    false_positive_rate: float
    true_positive_rate: float
    h1_seed_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class YokedCausationStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[YokedCausationSeedResult, ...]
    mean_false_positive_rate: float
    mean_true_positive_rate: float
    e1_fpr_gate: bool
    e1_tpr_gate: bool
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [item.as_dict() for item in self.per_seed],
            "mean_false_positive_rate": self.mean_false_positive_rate,
            "mean_true_positive_rate": self.mean_true_positive_rate,
            "e1_fpr_gate": self.e1_fpr_gate,
            "e1_tpr_gate": self.e1_tpr_gate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 64:
        raise ValueError("seeds must contain between 1 and 64 entries")
    if len(set(normalized)) != len(normalized):
        raise ValueError("seeds must be unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must contain integers only")
    return normalized


def _activation_schedule(rng: random.Random, steps: int) -> list[float]:
    """Generate intervention and resting trials before outcome generation.

    The schedule is evaluator apparatus state. AgencyModel receives only the
    resulting opaque activation magnitudes and opaque deltas.
    """
    activations: list[float] = []
    for _ in range(steps + 1):
        if rng.random() < 0.30:
            activations.append(0.0)
        else:
            activations.append(rng.uniform(0.25, 1.0))
    return activations


def _bounded_noise(rng: random.Random, sigma: float = 0.02) -> float:
    return max(-0.08, min(0.08, rng.gauss(0.0, sigma)))


def _run_seed(seed: int, *, steps: int) -> YokedCausationSeedResult:
    rng = random.Random(seed)
    activations = _activation_schedule(rng, steps)

    genuine = AgencyModel()
    yoked = AgencyModel()
    anticausal = AgencyModel()
    independent = AgencyModel()

    for tick in range(steps):
        act = activations[tick]
        next_act = activations[tick + 1]

        # Genuine physical consequence: current intervention causes current
        # evaluator-step sensory delta.
        genuine_delta = 0.38 * act + _bounded_noise(rng)

        # Yoked external consequence: produced by apparatus outside the body,
        # but matched to current activation statistics. This is intentionally
        # difficult and exposes the observational-identifiability limit.
        yoked_delta = 0.38 * act + _bounded_noise(rng)

        # Anti-causal control: sensory change is driven by a future activation,
        # not by the current intervention.
        anticausal_delta = 0.38 * next_act + _bounded_noise(rng)

        # Independent matched-scale environmental variation.
        independent_delta = rng.uniform(-0.20, 0.20)

        activation = {"out.0": act}
        genuine.record_step(activation, {"in.0": genuine_delta})
        yoked.record_step(activation, {"in.0": yoked_delta})
        anticausal.record_step(activation, {"in.0": anticausal_delta})
        independent.record_step(activation, {"in.0": independent_delta})

    def confidence(model: AgencyModel) -> float:
        return float(model.agency_confidence.get("out.0", 0.0))

    genuine_conf = confidence(genuine)
    yoked_conf = confidence(yoked)
    anticausal_conf = confidence(anticausal)
    independent_conf = confidence(independent)

    genuine_agentic = genuine_conf >= AGENCY_THRESHOLD
    false_flags = (
        yoked_conf >= AGENCY_THRESHOLD,
        anticausal_conf >= AGENCY_THRESHOLD,
        independent_conf >= AGENCY_THRESHOLD,
    )
    fpr = sum(1 for flag in false_flags if flag) / len(false_flags)
    tpr = 1.0 if genuine_agentic else 0.0
    h1_seed_pass = fpr <= MAX_FALSE_POSITIVE_RATE and tpr >= MIN_TRUE_POSITIVE_RATE

    return YokedCausationSeedResult(
        seed=seed,
        genuine_confidence=genuine_conf,
        yoked_confidence=yoked_conf,
        anticausal_confidence=anticausal_conf,
        independent_confidence=independent_conf,
        genuine_agentic=genuine_agentic,
        yoked_agentic=false_flags[0],
        anticausal_agentic=false_flags[1],
        independent_agentic=false_flags[2],
        false_positive_rate=fpr,
        true_positive_rate=tpr,
        h1_seed_pass=h1_seed_pass,
    )


def run_yoked_external_causation_study(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
    steps: int = 600,
) -> YokedCausationStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 50 or steps > 100_000:
        raise ValueError("steps must be within [50, 100000]")

    results = tuple(_run_seed(seed, steps=steps) for seed in normalized)
    replay = tuple(_run_seed(seed, steps=steps) for seed in normalized)

    replay_deterministic = results == replay
    mean_fpr = sum(item.false_positive_rate for item in results) / len(results)
    mean_tpr = sum(item.true_positive_rate for item in results) / len(results)
    fpr_gate = mean_fpr <= MAX_FALSE_POSITIVE_RATE
    tpr_gate = mean_tpr >= MIN_TRUE_POSITIVE_RATE

    return YokedCausationStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        mean_false_positive_rate=mean_fpr,
        mean_true_positive_rate=mean_tpr,
        e1_fpr_gate=fpr_gate,
        e1_tpr_gate=tpr_gate,
        replay_deterministic=replay_deterministic,
        h1_supported=fpr_gate and tpr_gate and replay_deterministic,
    )


__all__ = [
    "YokedCausationSeedResult",
    "YokedCausationStudy",
    "run_yoked_external_causation_study",
]
