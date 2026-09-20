"""E6 adversarial falsification study: hidden common-cause confound.

A hidden evaluator-side variable Z modulates both activation opportunity and an
external sensory channel. The subject never observes Z. This tests whether the
current intervention/baseline contrast can reject a confounded external channel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel

_STUDY_ID = "embodiment.hidden-common-cause"
THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class CommonCauseSeedResult:
    seed: int
    genuine_confidence: float
    confounded_confidence: float
    independent_confidence: float
    genuine_agentic: bool
    confounded_agentic: bool
    independent_agentic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HiddenCommonCauseStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[CommonCauseSeedResult, ...]
    true_positive_rate: float
    confounded_false_positive_rate: float
    independent_false_positive_rate: float
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [x.as_dict() for x in self.per_seed],
            "true_positive_rate": self.true_positive_rate,
            "confounded_false_positive_rate": self.confounded_false_positive_rate,
            "independent_false_positive_rate": self.independent_false_positive_rate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    result = tuple(seeds)
    if not result or len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(s, bool) or not isinstance(s, int) for s in result):
        raise ValueError("seeds must contain integers only")
    return result


def _run_seed(seed: int, *, steps: int) -> CommonCauseSeedResult:
    rng = random.Random(seed)
    genuine = AgencyModel()
    confounded = AgencyModel()
    independent = AgencyModel()

    for _ in range(steps):
        # Hidden world state changes activation propensity but is not caused by
        # the subject and is never exposed as an input label.
        z = 1.0 if rng.random() < 0.5 else 0.0
        active_prob = 0.90 if z > 0.5 else 0.20
        act = rng.uniform(0.25, 1.0) if rng.random() < active_prob else 0.0

        genuine_delta = 0.38 * act + rng.gauss(0.0, 0.015)
        confounded_delta = 0.30 * z + rng.gauss(0.0, 0.015)
        independent_delta = rng.uniform(-0.18, 0.18)

        activation = {"out.0": act}
        genuine.record_step(activation, {"in.0": genuine_delta})
        confounded.record_step(activation, {"in.0": confounded_delta})
        independent.record_step(activation, {"in.0": independent_delta})

    def conf(model: AgencyModel) -> float:
        return float(model.agency_confidence.get("out.0", 0.0))

    gc, cc, ic = conf(genuine), conf(confounded), conf(independent)
    return CommonCauseSeedResult(
        seed=seed,
        genuine_confidence=gc,
        confounded_confidence=cc,
        independent_confidence=ic,
        genuine_agentic=gc >= THRESHOLD,
        confounded_agentic=cc >= THRESHOLD,
        independent_agentic=ic >= THRESHOLD,
    )


def run_hidden_common_cause_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
    steps: int = 600,
) -> HiddenCommonCauseStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 50 or steps > 100_000:
        raise ValueError("steps must be within [50,100000]")
    results = tuple(_run_seed(s, steps=steps) for s in normalized)
    replay = tuple(_run_seed(s, steps=steps) for s in normalized)
    n = len(results)
    tpr = sum(x.genuine_agentic for x in results)/n
    cfpr = sum(x.confounded_agentic for x in results)/n
    ifpr = sum(x.independent_agentic for x in results)/n
    deterministic = results == replay
    supported = tpr >= 0.70 and cfpr <= 0.10 and ifpr <= 0.10 and deterministic
    return HiddenCommonCauseStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        true_positive_rate=tpr,
        confounded_false_positive_rate=cfpr,
        independent_false_positive_rate=ifpr,
        replay_deterministic=deterministic,
        h1_supported=supported,
    )
