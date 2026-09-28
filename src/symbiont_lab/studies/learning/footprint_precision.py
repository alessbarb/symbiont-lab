"""FP-0: footprint membership against the E8 body's ground truth.

Footprint Precision v1 §3 (preregistered at 02ad29be). Descriptive only: the
organism runs unchanged; the evaluator maps opaque channels to actuators and
atom features to receptors, which never reaches cognition.
"""

from __future__ import annotations

from typing import Any, Sequence

from symbiont.actuation.intervention import opaque_channel_ref

from .agency_acquisition import DEFAULT_SEEDS, _seeds
from .agency_acquisition_body import CausalBody, build_subject

SNAPSHOT_TICKS = (500, 1000, 1500, 2000, 2500, 3000)
# Footprint Precision v1 §6 arms: (quiet_near, multiplicity).
MEMBERSHIP_ARMS = {"R": (None, False), "T": (8, False), "M": (None, True), "TM": (8, True)}


def apply_membership(runtime, membership: str) -> None:
    if membership not in MEMBERSHIP_ARMS:
        raise ValueError(f"membership must be one of {sorted(MEMBERSHIP_ARMS)}")
    quiet_near, multiplicity = MEMBERSHIP_ARMS[membership]
    runtime._action_domain.acquisition.set_footprint_membership(
        quiet_near=quiet_near, multiplicity=multiplicity
    )


def _classify(runtime, body: CausalBody) -> dict[str, Any]:
    acquisition = runtime._action_domain.acquisition
    actuator_of = {opaque_channel_ref(a): a for a in body.surface.actuator_ids}
    receptor_of = {runtime._signal_identity.signal_id(r): r for r in body.receptor_ids}
    driven_by = {
        receptor: actuator
        for actuator in body.surface.actuator_ids
        for receptor in body.driven_receptors(actuator)
    }
    drifting = set(body._drifting_ids)
    counts = {"own": 0, "cross": 0, "drift": 0, "other": 0}
    members: list[dict[str, Any]] = []
    recall_hits = recall_total = 0
    for source, atom_ids in sorted(acquisition.footprints.footprints.items()):
        actuators = {actuator_of.get(channel) for channel in source}
        estimates = acquisition.footprints.member_estimates(source)
        own_receptors = set()
        for atom_id in sorted(atom_ids):
            atom = acquisition._atom_catalog.get(atom_id)
            receptor = receptor_of.get(atom.feature_ref) if atom is not None else None
            if receptor is not None and driven_by.get(receptor) in actuators:
                kind = "own"
                own_receptors.add(receptor)
            elif receptor in driven_by:
                kind = "cross"
            elif receptor in drifting:
                kind = "drift"
            else:
                kind = "other"
            counts[kind] += 1
            estimate = estimates[atom_id]
            members.append(
                {
                    "kind": kind,
                    "sources": len(source),
                    "magnitude_class": atom.magnitude_class if atom is not None else None,
                    "pulses": estimate.pulses,
                    "hits": estimate.hits,
                    "passive_windows": estimate.passive_windows,
                    "passive_hits": estimate.passive_hits,
                    "expected_quiet_rate": estimate.expected_quiet_rate,
                    "pulse_rate_lower_bound": estimate.pulse_rate_lower_bound,
                }
            )
        if len(source) == 1 and (actuator := actuator_of.get(source[0])) is not None:
            driven = set(body.driven_receptors(actuator))
            recall_total += len(driven)
            recall_hits += len(driven & own_receptors)
    total = sum(counts.values())
    return {
        "footprints": len(acquisition.footprints.footprints),
        "members": total,
        "by_class": counts,
        "precision": counts["own"] / total if total else None,
        "recall": recall_hits / recall_total if recall_total else None,
        "member_details": members,
    }


def run_footprint_precision_study(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    ticks: int = 3000,
    actuator_count: int = 16,
    receptors_per_actuator: int = 4,
    drifting_receptor_count: int = 32,
    membership: str = "R",
) -> dict[str, Any]:
    resolved = _seeds(seeds)
    snapshots = tuple(tick for tick in SNAPSHOT_TICKS if tick <= ticks) or (ticks,)
    per_seed = []
    for seed in resolved:
        body = CausalBody(
            actuator_count=actuator_count,
            seed=seed,
            receptors_per_actuator=receptors_per_actuator,
            drifting_receptor_count=drifting_receptor_count,
        )
        runtime = build_subject(
            body, organism_id=f"footprint-precision-{seed}", factorized_effects=True
        )
        apply_membership(runtime, membership)
        rows = {}
        for tick in range(1, ticks + 1):
            runtime.tick()
            body.advance(runtime.last_actuations)
            if tick in snapshots:
                rows[str(tick)] = _classify(runtime, body)
        per_seed.append({"seed": seed, "snapshots": rows})
    return {
        "protocol": "learning.footprint-precision",
        "membership": membership,
        "seeds": list(resolved),
        "ticks": ticks,
        "snapshot_ticks": list(snapshots),
        "per_seed": per_seed,
        "decision_inputs": _decision_inputs(per_seed, str(snapshots[-1])),
    }


def _decision_inputs(per_seed: list[dict[str, Any]], final: str) -> dict[str, Any]:
    """§3 decision rule inputs, pooled over seeds at the final snapshot."""
    wrong = [
        member
        for row in per_seed
        for member in row["snapshots"][final]["member_details"]
        if member["kind"] in ("drift", "cross")
    ]
    n = len(wrong)
    zero_quiet = sum(1 for member in wrong if member["passive_hits"] == 0)
    few_pulses = sum(1 for member in wrong if member["pulses"] <= 6)
    rule = (
        "H1"
        if n and zero_quiet / n >= 0.5
        else ("H2" if n and few_pulses / n >= 0.5 else ("H3" if n else None))
    )
    return {
        "wrong_members": n,
        "zero_passive_hits_fraction": zero_quiet / n if n else None,
        "pulses_le_6_fraction": few_pulses / n if n else None,
        "selected_hypothesis": rule,
    }


__all__ = ["MEMBERSHIP_ARMS", "SNAPSHOT_TICKS", "apply_membership", "run_footprint_precision_study"]
