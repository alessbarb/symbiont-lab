"""E1 adversarial falsification study: yoked external causation.

Preregistered in:
research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md

This implementation covers exact yoking, jittered yoking, anti-causal ordering,
independent control, break-of-yoking rejection latency and lead/lag reporting.
Evaluator truth remains entirely in symbiont_lab.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.core.embodiment.agency import AgencyModel

# Component-level falsification specimen marker (see §62 of
# docs/design/herencia-evolutiva-multidimensional.md). This module
# freshly constructs isolated AgencyModel/InferredBodySchema specimens
# purely to falsify the algorithm itself. It never imports or
# constructs a live Symbiont/Individual, never attaches a specimen to
# one, and never crosses synthetic state back into cognition. Checked
# structurally and at runtime by
# tests/experimental_integrity/test_embodiment_inheritance_integrity.py.
__falsification_specimen__ = True

_STUDY_ID = "embodiment.yoked-external-causation"
AGENCY_THRESHOLD = 0.5
MAX_FALSE_POSITIVE_RATE = 0.10
MIN_TRUE_POSITIVE_RATE = 0.70


@dataclass(frozen=True, slots=True)
class YokedCausationSeedResult:
    seed: int
    genuine_confidence: float
    exact_yoked_confidence: float
    jittered_yoked_confidence: float
    anticausal_confidence: float
    independent_confidence: float
    broken_yoke_final_confidence: float
    broken_yoke_rejection_latency: int | None
    exact_lag0_correlation: float
    exact_lag1_correlation: float
    genuine_agentic: bool
    exact_yoked_agentic: bool
    jittered_yoked_agentic: bool
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
    mean_broken_yoke_final_confidence: float
    broken_yoke_rejection_rate: float
    e1_fpr_gate: bool
    e1_tpr_gate: bool
    e1_break_rejection_gate: bool
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
            "mean_broken_yoke_final_confidence": self.mean_broken_yoke_final_confidence,
            "broken_yoke_rejection_rate": self.broken_yoke_rejection_rate,
            "e1_fpr_gate": self.e1_fpr_gate,
            "e1_tpr_gate": self.e1_tpr_gate,
            "e1_break_rejection_gate": self.e1_break_rejection_gate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 64 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must contain integers only")
    return normalized


def _activation_schedule(rng: random.Random, steps: int) -> list[float]:
    return [0.0 if rng.random() < 0.30 else rng.uniform(0.25, 1.0) for _ in range(steps + 3)]


def _bounded_noise(rng: random.Random, sigma: float = 0.02) -> float:
    return max(-0.08, min(0.08, rng.gauss(0.0, sigma)))


def _corr(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx <= 1e-12 or dy <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, num / (dx * dy)))


def _confidence(model: AgencyModel) -> float:
    return float(model.agency_confidence.get("out.0", 0.0))


def _run_seed(seed: int, *, steps: int) -> YokedCausationSeedResult:
    rng = random.Random(seed)
    acts = _activation_schedule(rng, steps)

    genuine = AgencyModel()
    exact = AgencyModel()
    jittered = AgencyModel()
    anticausal = AgencyModel()
    independent = AgencyModel()
    broken = AgencyModel()

    exact_deltas: list[float] = []
    break_tick = steps // 2
    rejection_latency: int | None = None

    for tick in range(steps):
        act = acts[tick]
        next_act = acts[tick + 1]
        previous_act = acts[tick - 1] if tick else 0.0

        genuine_delta = 0.38 * act + _bounded_noise(rng)
        exact_delta = 0.38 * act + _bounded_noise(rng)

        # Jittered external yoke: external process sometimes follows current
        # activation and sometimes the immediately previous activation.
        source = act if rng.random() < 0.65 else previous_act
        jittered_delta = 0.38 * source + _bounded_noise(rng)

        anticausal_delta = 0.38 * next_act + _bounded_noise(rng)
        independent_delta = rng.uniform(-0.20, 0.20)

        # First half is perfectly yoked. At break_tick the external process is
        # physically decoupled and becomes independent without any subject marker.
        if tick < break_tick:
            broken_delta = 0.38 * act + _bounded_noise(rng)
        else:
            broken_delta = rng.uniform(-0.20, 0.20)

        activation = {"out.0": act}
        genuine.record_step(activation, {"in.0": genuine_delta})
        exact.record_step(activation, {"in.0": exact_delta})
        jittered.record_step(activation, {"in.0": jittered_delta})
        anticausal.record_step(activation, {"in.0": anticausal_delta})
        independent.record_step(activation, {"in.0": independent_delta})
        broken.record_step(activation, {"in.0": broken_delta})

        exact_deltas.append(exact_delta)

        if tick >= break_tick and rejection_latency is None:
            if _confidence(broken) < AGENCY_THRESHOLD:
                rejection_latency = tick - break_tick

    gc = _confidence(genuine)
    ec = _confidence(exact)
    jc = _confidence(jittered)
    ac = _confidence(anticausal)
    ic = _confidence(independent)
    bc = _confidence(broken)

    false_flags = (
        ec >= AGENCY_THRESHOLD,
        jc >= AGENCY_THRESHOLD,
        ac >= AGENCY_THRESHOLD,
        ic >= AGENCY_THRESHOLD,
    )
    fpr = sum(false_flags) / len(false_flags)
    tpr = 1.0 if gc >= AGENCY_THRESHOLD else 0.0

    # Evaluator-only temporal diagnostics.
    lag0 = _corr(acts[:steps], exact_deltas)
    lag1 = _corr(acts[: steps - 1], exact_deltas[1:])

    break_rejected = rejection_latency is not None
    h1_seed_pass = (
        fpr <= MAX_FALSE_POSITIVE_RATE and tpr >= MIN_TRUE_POSITIVE_RATE and break_rejected
    )

    return YokedCausationSeedResult(
        seed=seed,
        genuine_confidence=gc,
        exact_yoked_confidence=ec,
        jittered_yoked_confidence=jc,
        anticausal_confidence=ac,
        independent_confidence=ic,
        broken_yoke_final_confidence=bc,
        broken_yoke_rejection_latency=rejection_latency,
        exact_lag0_correlation=lag0,
        exact_lag1_correlation=lag1,
        genuine_agentic=gc >= AGENCY_THRESHOLD,
        exact_yoked_agentic=false_flags[0],
        jittered_yoked_agentic=false_flags[1],
        anticausal_agentic=false_flags[2],
        independent_agentic=false_flags[3],
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
    if steps < 100 or steps > 100_000:
        raise ValueError("steps must be within [100,100000]")

    results = tuple(_run_seed(seed, steps=steps) for seed in normalized)
    replay = tuple(_run_seed(seed, steps=steps) for seed in normalized)

    mean_fpr = sum(x.false_positive_rate for x in results) / len(results)
    mean_tpr = sum(x.true_positive_rate for x in results) / len(results)
    mean_broken = sum(x.broken_yoke_final_confidence for x in results) / len(results)
    rejection_rate = sum(x.broken_yoke_rejection_latency is not None for x in results) / len(
        results
    )
    deterministic = results == replay

    fpr_gate = mean_fpr <= MAX_FALSE_POSITIVE_RATE
    tpr_gate = mean_tpr >= MIN_TRUE_POSITIVE_RATE
    break_gate = rejection_rate >= 0.70

    return YokedCausationStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        mean_false_positive_rate=mean_fpr,
        mean_true_positive_rate=mean_tpr,
        mean_broken_yoke_final_confidence=mean_broken,
        broken_yoke_rejection_rate=rejection_rate,
        e1_fpr_gate=fpr_gate,
        e1_tpr_gate=tpr_gate,
        e1_break_rejection_gate=break_gate,
        replay_deterministic=deterministic,
        h1_supported=fpr_gate and tpr_gate and break_gate and deterministic,
    )


__all__ = [
    "YokedCausationSeedResult",
    "YokedCausationStudy",
    "run_yoked_external_causation_study",
]
