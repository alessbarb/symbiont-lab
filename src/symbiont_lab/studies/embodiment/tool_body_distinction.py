"""E2 adversarial falsification study: controllable external tool vs body.

Preregistered in:
research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md

The assay compares four channels:
- direct bodily consequence,
- attached external tool consequence,
- detached but remotely controllable external object,
- uncontrollable external object.

The current body-boundary mechanism is challenged on whether it can distinguish
causal integration from mere controllability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel, InferredBodySchema, PerceptualStructure

_STUDY_ID = "embodiment.tool-body-distinction"
THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class ToolBodySeedResult:
    seed: int
    body_internal: bool
    attached_tool_internal: bool
    remote_object_internal: bool
    uncontrolled_external_internal: bool
    body_score: float
    attached_score: float
    remote_score: float
    uncontrolled_score: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ToolBodyDistinctionStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[ToolBodySeedResult, ...]
    body_detection_rate: float
    attached_assimilation_rate: float
    remote_assimilation_rate: float
    uncontrolled_assimilation_rate: float
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [x.as_dict() for x in self.per_seed],
            "body_detection_rate": self.body_detection_rate,
            "attached_assimilation_rate": self.attached_assimilation_rate,
            "remote_assimilation_rate": self.remote_assimilation_rate,
            "uncontrolled_assimilation_rate": self.uncontrolled_assimilation_rate,
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


def _run_seed(seed: int, *, steps: int) -> ToolBodySeedResult:
    rng = random.Random(seed)
    p = PerceptualStructure()
    a = AgencyModel()
    schema = InferredBodySchema()

    body_v = attached_v = remote_v = external_v = 0.0

    for _ in range(steps):
        act = 0.0 if rng.random() < 0.30 else rng.uniform(0.25, 1.0)
        noise = lambda: rng.gauss(0.0, 0.015)

        body_delta = 0.40 * act + noise()
        body_v = max(-1.0, min(1.0, 0.55 * body_v + body_delta))

        # Attached tool: tightly and persistently coupled via the body.
        attached_target = 0.75 * body_v + noise()
        attached_delta = attached_target - attached_v
        attached_v = max(-1.0, min(1.0, attached_target))

        # Remote object: equally controllable from activation statistics, but
        # physically detached from Body.
        remote_delta = 0.40 * act + noise()
        remote_v = max(-1.0, min(1.0, 0.55 * remote_v + remote_delta))

        # Uncontrolled external baseline.
        external_target = 0.70 * external_v + rng.uniform(-0.12, 0.12)
        external_delta = external_target - external_v
        external_v = max(-1.0, min(1.0, external_target))

        inputs = {
            "in.body": body_v,
            "in.attached": attached_v,
            "in.remote": remote_v,
            "in.external": external_v,
        }
        deltas = {
            "in.body": body_delta,
            "in.attached": attached_delta,
            "in.remote": remote_delta,
            "in.external": external_delta,
        }
        p.observe(inputs)
        a.record_step({"out.0": act}, deltas)

    schema.update_from_agency(a, p)

    return ToolBodySeedResult(
        seed=seed,
        body_internal="in.body" in schema.internal_channels,
        attached_tool_internal="in.attached" in schema.internal_channels,
        remote_object_internal="in.remote" in schema.internal_channels,
        uncontrolled_external_internal="in.external" in schema.internal_channels,
        body_score=float(a.controllability.get("in.body", 0.0)),
        attached_score=float(a.controllability.get("in.attached", 0.0)),
        remote_score=float(a.controllability.get("in.remote", 0.0)),
        uncontrolled_score=float(a.controllability.get("in.external", 0.0)),
    )


def run_tool_body_distinction_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
    steps: int = 600,
) -> ToolBodyDistinctionStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 50 or steps > 100_000:
        raise ValueError("steps must be within [50,100000]")
    results = tuple(_run_seed(s, steps=steps) for s in normalized)
    replay = tuple(_run_seed(s, steps=steps) for s in normalized)
    n = len(results)
    rate = lambda attr: sum(bool(getattr(x, attr)) for x in results) / n
    body_rate = rate("body_internal")
    attached_rate = rate("attached_tool_internal")
    remote_rate = rate("remote_object_internal")
    uncontrolled_rate = rate("uncontrolled_external_internal")
    deterministic = results == replay

    # Attached-tool assimilation is not itself considered failure. The decisive
    # gate is whether the detached remote object is rejected.
    supported = (
        body_rate >= 0.70
        and remote_rate <= 0.10
        and uncontrolled_rate <= 0.10
        and deterministic
    )

    return ToolBodyDistinctionStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        body_detection_rate=body_rate,
        attached_assimilation_rate=attached_rate,
        remote_assimilation_rate=remote_rate,
        uncontrolled_assimilation_rate=uncontrolled_rate,
        replay_deterministic=deterministic,
        h1_supported=supported,
    )
