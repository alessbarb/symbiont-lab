"""BD-1: binding invalidation against a binding's own history, with ground truth.

Binding Degradation v1 §3 (preregistered at e47c4042). The E8 body loses its
first effector at ``break_tick``; the evaluator knows which bindings are
truly degraded (their competence drives that actuator) and which are only at
risk of a false invalidation. The organism never sees the classification.
"""

from __future__ import annotations

from typing import Any, Sequence

from symbiont.actuation.binding import BindingStatus
from symbiont.agency.intention import IntentStatus

from .agency_acquisition import _intent_terminations, _seeds
from .agency_acquisition_body import BodyCondition, CausalBody, build_subject

BD1_SEEDS = (409, 419, 421, 431, 433, 439, 443, 449, 457, 461)
ARMS = {"OFF": "off", "HIST": "history"}


def _actuators_of(domain, competence_id: str) -> set[str]:
    engine = domain._competence_development
    actuators: set[str] = set()
    for leaf in domain._flatten_competence_controller(competence_id):
        primitive = engine._primitives.get(leaf) if engine is not None else None
        if primitive is None:
            continue
        for pattern in primitive.sequence:
            actuators.update(actuator for actuator, level in pattern if level > 0)
    return actuators


def _seed(
    seed: int, *, arm: str, ticks: int, break_tick: int, body_options: dict[str, int]
) -> dict[str, Any]:
    body = CausalBody(
        actuator_count=body_options["actuator_count"],
        seed=seed,
        receptors_per_actuator=body_options["receptors_per_actuator"],
        drifting_receptor_count=body_options["drifting_receptor_count"],
    )
    runtime = build_subject(
        body, organism_id=f"binding-degradation-{seed}", factorized_effects=True
    )
    domain = runtime._action_domain
    domain.binding_invalidation = ARMS[arm]
    terminations = _intent_terminations(runtime, body)
    broken = body.surface.actuator_ids[0]
    degraded: set[str] = set()
    at_risk: set[str] = set()
    invalidated_before_break: set[str] = set()
    for tick in range(1, ticks + 1):
        if tick == break_tick:
            invalidated_before_break = {
                b.competence_id
                for b in domain.execution_bindings.items
                if b.status is BindingStatus.INVALIDATED
            }
            for binding in domain.execution_bindings.items:
                if binding.status is not BindingStatus.VALID:
                    continue
                if broken in _actuators_of(domain, binding.competence_id):
                    degraded.add(binding.competence_id)
                else:
                    at_risk.add(binding.competence_id)
            body.set_condition(BodyCondition.BROKEN_EFFECTOR)
        runtime.tick()
        body.advance(runtime.last_actuations)
    final = {b.competence_id: b for b in domain.execution_bindings.items}
    invalidated = {cid for cid, b in final.items() if b.status is BindingStatus.INVALIDATED}
    latencies = [
        final[cid].status_changed_tick - break_tick
        for cid in degraded & invalidated
        if final[cid].status_changed_tick >= break_tick
    ]
    outcome = terminations()
    return {
        "seed": seed,
        "degraded": len(degraded),
        "at_risk": len(at_risk),
        "true_detections": len(degraded & invalidated),
        "false_invalidations": len(at_risk & invalidated),
        "invalidated_before_break": len(invalidated_before_break),
        "detection_latencies": sorted(latencies),
        "intents_satisfied": domain.intention.counts[IntentStatus.SATISFIED],
        "spurious_satisfactions": outcome["spurious_satisfactions"],
        "executable_competences_end": sum(
            1 for c in domain.competence_library.items if domain.competence_is_executable(c)
        ),
    }


def run_binding_degradation_study(
    *,
    seeds: Sequence[int] = BD1_SEEDS,
    ticks: int = 4000,
    break_tick: int = 2000,
    arm: str = "HIST",
    actuator_count: int = 16,
    receptors_per_actuator: int = 4,
    drifting_receptor_count: int = 32,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {sorted(ARMS)}")
    resolved = _seeds(seeds)
    body_options = {
        "actuator_count": actuator_count,
        "receptors_per_actuator": receptors_per_actuator,
        "drifting_receptor_count": drifting_receptor_count,
    }
    per_seed = [
        _seed(seed, arm=arm, ticks=ticks, break_tick=break_tick, body_options=body_options)
        for seed in resolved
    ]
    pooled = {
        key: sum(row[key] for row in per_seed)
        for key in (
            "degraded",
            "at_risk",
            "true_detections",
            "false_invalidations",
            "invalidated_before_break",
            "intents_satisfied",
            "spurious_satisfactions",
        )
    }
    return {
        "protocol": "learning.binding-degradation",
        "arm": arm,
        "seeds": list(resolved),
        "ticks": ticks,
        "break_tick": break_tick,
        "per_seed": per_seed,
        "pooled": pooled,
        "false_invalidation_rate": (
            pooled["false_invalidations"] / pooled["at_risk"] if pooled["at_risk"] else None
        ),
        "detection_rate": (
            pooled["true_detections"] / pooled["degraded"] if pooled["degraded"] >= 5 else None
        ),
    }


__all__ = ["ARMS", "BD1_SEEDS", "run_binding_degradation_study"]
