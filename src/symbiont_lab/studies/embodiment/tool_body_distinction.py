"""E2 adversarial falsification study: controllable external tool vs body.

Uses a real Body effector and EmbodimentSession. An attached external tool is
driven by the body's physical effector consequence, a remote detached object is
controlled directly by the same opaque activation statistics, and an
uncontrolled object provides a negative control. Mid-run the attached tool is
physically decoupled without notifying cognition.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel, InferredBodySchema, PerceptualStructure
from symbiont.core.body import Body, BodyPhysiology, EffectorPort, ReceptorPort
from symbiont.core.embodiment import implant_body

# Component-level falsification specimen marker (see §62 of
# docs/design/herencia-evolutiva-multidimensional.md). This module
# freshly constructs isolated AgencyModel/InferredBodySchema specimens,
# together with a fresh apparatus Body/EmbodimentSession (bound to a
# bare symbiont_id string, never a live Symbiont/Individual instance),
# purely to falsify the algorithm itself. It never imports or
# constructs a live Symbiont/Individual, never attaches a specimen to
# one, and never crosses synthetic state back into cognition. Checked
# structurally and at runtime by
# tests/experimental_integrity/test_embodiment_inheritance_integrity.py.
__falsification_specimen__ = True

_STUDY_ID = "embodiment.tool-body-distinction"


@dataclass(frozen=True, slots=True)
class ToolBodySeedResult:
    seed: int
    body_internal: bool
    attached_before_decouple_internal: bool
    attached_after_decouple_internal: bool
    remote_object_internal: bool
    uncontrolled_external_internal: bool
    body_score: float
    attached_score: float
    remote_score: float
    uncontrolled_score: float
    revision_count_delta_after_decouple: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ToolBodyDistinctionStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[ToolBodySeedResult, ...]
    body_detection_rate: float
    attached_pre_assimilation_rate: float
    attached_post_assimilation_rate: float
    remote_assimilation_rate: float
    uncontrolled_assimilation_rate: float
    decoupling_revision_rate: float
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [x.as_dict() for x in self.per_seed],
            "body_detection_rate": self.body_detection_rate,
            "attached_pre_assimilation_rate": self.attached_pre_assimilation_rate,
            "attached_post_assimilation_rate": self.attached_post_assimilation_rate,
            "remote_assimilation_rate": self.remote_assimilation_rate,
            "uncontrolled_assimilation_rate": self.uncontrolled_assimilation_rate,
            "decoupling_revision_rate": self.decoupling_revision_rate,
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

    physiology = BodyPhysiology(
        energy_reserve=100.0,
        max_energy=100.0,
        basal_metabolic_rate=0.0,
        degradation_rate=0.0,
    )
    eff = EffectorPort(
        port_id=f"eff-{seed}",
        kind="impulse",
        ordinal=0,
        efficiency=1.0,
        cost_per_activation=0.01,
    )

    attached_state = [0.0]
    remote_state = [0.0]
    uncontrolled_state = [0.0]

    body_sensor = ReceptorPort(
        port_id=f"body-sense-{seed}",
        kind="proprioceptive",
        ordinal=0,
        read_fn=lambda: eff.last_consequence,
    )
    attached_sensor = ReceptorPort(
        port_id=f"attached-sense-{seed}",
        kind="exteroceptive",
        ordinal=1,
        read_fn=lambda: attached_state[0],
    )
    remote_sensor = ReceptorPort(
        port_id=f"remote-sense-{seed}",
        kind="exteroceptive",
        ordinal=2,
        read_fn=lambda: remote_state[0],
    )
    uncontrolled_sensor = ReceptorPort(
        port_id=f"external-sense-{seed}",
        kind="exteroceptive",
        ordinal=3,
        read_fn=lambda: uncontrolled_state[0],
    )

    body = Body(
        f"e2-body-{seed}",
        morphology_name="e2-tool-assay",
        receptors=(body_sensor, attached_sensor, remote_sensor, uncontrolled_sensor),
        effectors=(eff,),
        physiology=physiology,
    )
    session = implant_body(f"e2-sym-{seed}", body)

    perceptual = PerceptualStructure()
    agency = AgencyModel()
    schema = InferredBodySchema()

    previous: dict[str, float] | None = None
    break_tick = steps // 2
    attached_before = False
    revisions_at_break = 0

    for tick in range(steps):
        act = 0.0 if rng.random() < 0.30 else rng.uniform(0.25, 1.0)
        consequences = body.apply_activations({eff.port_id: act})
        physical_effect = consequences[eff.port_id].physical_effect

        if tick < break_tick:
            # Physically attached tool: consequence propagates from Body effect.
            attached_state[0] = max(
                0.0,
                min(1.0, 0.55 * attached_state[0] + 0.45 * physical_effect),
            )
        else:
            # Decoupled: external tool retains its own dynamics and no longer
            # receives bodily physical effect.
            attached_state[0] = max(
                0.0,
                min(1.0, 0.80 * attached_state[0] + rng.uniform(-0.06, 0.06)),
            )

        # Detached remotely controllable object: deliberately controllable but
        # not mediated by Body's physical consequence.
        remote_state[0] = max(
            0.0,
            min(1.0, 0.55 * remote_state[0] + 0.45 * act),
        )

        uncontrolled_state[0] = max(
            0.0,
            min(1.0, 0.75 * uncontrolled_state[0] + rng.uniform(-0.12, 0.12)),
        )

        opaque = session.transduce_to_symbiont(body.transduce_signals())
        perceptual.observe(opaque)

        if previous is not None:
            deltas = {ch: v - previous.get(ch, v) for ch, v in opaque.items()}
            agency.record_step({"out.0": act}, deltas)
        previous = dict(opaque)

        schema.update_from_agency(agency, perceptual)

        if tick == break_tick - 1:
            attached_before = "in.1" in schema.internal_channels
            revisions_at_break = schema.revision_count

    attached_after = "in.1" in schema.internal_channels

    return ToolBodySeedResult(
        seed=seed,
        body_internal="in.0" in schema.internal_channels,
        attached_before_decouple_internal=attached_before,
        attached_after_decouple_internal=attached_after,
        remote_object_internal="in.2" in schema.internal_channels,
        uncontrolled_external_internal="in.3" in schema.internal_channels,
        body_score=float(agency.controllability.get("in.0", 0.0)),
        attached_score=float(agency.controllability.get("in.1", 0.0)),
        remote_score=float(agency.controllability.get("in.2", 0.0)),
        uncontrolled_score=float(agency.controllability.get("in.3", 0.0)),
        revision_count_delta_after_decouple=max(0, schema.revision_count - revisions_at_break),
    )


def run_tool_body_distinction_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
    steps: int = 600,
) -> ToolBodyDistinctionStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 100 or steps > 100_000:
        raise ValueError("steps must be within [100,100000]")

    results = tuple(_run_seed(s, steps=steps) for s in normalized)
    replay = tuple(_run_seed(s, steps=steps) for s in normalized)
    n = len(results)
    rate = lambda attr: sum(bool(getattr(x, attr)) for x in results) / n

    body_rate = rate("body_internal")
    attached_pre = rate("attached_before_decouple_internal")
    attached_post = rate("attached_after_decouple_internal")
    remote_rate = rate("remote_object_internal")
    uncontrolled_rate = rate("uncontrolled_external_internal")
    revision_rate = sum(x.revision_count_delta_after_decouple > 0 for x in results) / n
    deterministic = results == replay

    # Attached assimilation before decoupling is allowed. After decoupling it
    # should fall, and a detached remote object should not be bodily merely
    # because it is controllable.
    supported = (
        body_rate >= 0.70
        and remote_rate <= 0.10
        and uncontrolled_rate <= 0.10
        and attached_post <= 0.10
        and revision_rate >= 0.70
        and deterministic
    )

    return ToolBodyDistinctionStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        body_detection_rate=body_rate,
        attached_pre_assimilation_rate=attached_pre,
        attached_post_assimilation_rate=attached_post,
        remote_assimilation_rate=remote_rate,
        uncontrolled_assimilation_rate=uncontrolled_rate,
        decoupling_revision_rate=revision_rate,
        replay_deterministic=deterministic,
        h1_supported=supported,
    )


__all__ = [
    "ToolBodySeedResult",
    "ToolBodyDistinctionStudy",
    "run_tool_body_distinction_study",
]
