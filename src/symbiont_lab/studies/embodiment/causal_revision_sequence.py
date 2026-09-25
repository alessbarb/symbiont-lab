"""E4 adversarial falsification study: sham, permutation, break, transplant.

The evaluator changes only physical coupling. The Symbiont receives no phase
marker, body identity, perturbation label or transplant notification.

Reports prediction shock, first revision latency, recovery latency and causal
mapping signatures before/after each phase.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from symbiont.core.body import Body, create_standard_body
from symbiont.core.individual import Individual, create_individual

_STUDY_ID = "embodiment.causal-revision-sequence"


@dataclass(frozen=True, slots=True)
class PhaseResult:
    name: str
    mean_prediction_error: float
    initial_prediction_error: float
    final_prediction_error: float
    prediction_shock: float
    disruption_ticks: int
    revision_delta: int
    first_revision_latency: int | None
    recovery_latency: int | None
    mean_schema_confidence: float
    mapping_before: tuple[tuple[str, str], ...]
    mapping_after: tuple[tuple[str, str], ...]
    mapping_changed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CausalRevisionSeedResult:
    seed: int
    phases: tuple[PhaseResult, ...]
    sham_error_delta: float
    permutation_error_delta: float
    break_error_delta: float
    transplant_error_delta: float
    permutation_revision: bool
    break_revision: bool
    transplant_revision: bool
    permutation_mapping_changed: bool
    transplant_mapping_changed: bool
    return_a_faster_than_transplant: bool
    sham_quieter_than_real_changes: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "phases": [p.as_dict() for p in self.phases],
            "sham_error_delta": self.sham_error_delta,
            "permutation_error_delta": self.permutation_error_delta,
            "break_error_delta": self.break_error_delta,
            "transplant_error_delta": self.transplant_error_delta,
            "permutation_revision": self.permutation_revision,
            "break_revision": self.break_revision,
            "transplant_revision": self.transplant_revision,
            "permutation_mapping_changed": self.permutation_mapping_changed,
            "transplant_mapping_changed": self.transplant_mapping_changed,
            "return_a_faster_than_transplant": self.return_a_faster_than_transplant,
            "sham_quieter_than_real_changes": self.sham_quieter_than_real_changes,
        }


@dataclass(frozen=True, slots=True)
class CausalRevisionStudy:
    seeds: tuple[int, ...]
    phase_ticks: int
    per_seed: tuple[CausalRevisionSeedResult, ...]
    permutation_revision_rate: float
    break_revision_rate: float
    transplant_revision_rate: float
    permutation_mapping_change_rate: float
    transplant_mapping_change_rate: float
    return_a_reacquisition_advantage_rate: float
    sham_specificity_rate: float
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "phase_ticks": self.phase_ticks,
            "per_seed": [item.as_dict() for item in self.per_seed],
            "permutation_revision_rate": self.permutation_revision_rate,
            "break_revision_rate": self.break_revision_rate,
            "transplant_revision_rate": self.transplant_revision_rate,
            "permutation_mapping_change_rate": self.permutation_mapping_change_rate,
            "transplant_mapping_change_rate": self.transplant_mapping_change_rate,
            "return_a_reacquisition_advantage_rate": self.return_a_reacquisition_advantage_rate,
            "sham_specificity_rate": self.sham_specificity_rate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    result = tuple(seeds)
    if not result or len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _stabilize_body(body: Body) -> None:
    body.physiology.max_energy = 10.0
    body.physiology.energy_reserve = 10.0
    body.basal_metabolic_rate = 0.001
    body.degradation_rate = 0.00005


def _tick_error(ind: Individual) -> float:
    return float(ind.symbiont.last_prediction_error)


def _mapping_signature(ind: Individual) -> tuple[tuple[str, str], ...]:
    """Observer-side projection of current opaque action->input mapping."""
    return ind.symbiont.inferred_mapping_signature()


def _feedback(
    *,
    body_variant: str,
    previous_effects: Mapping[str, float],
    rng: random.Random,
) -> dict[str, float]:
    e0 = float(previous_effects.get("eff.0", 0.0))
    e1 = float(previous_effects.get("eff.1", 0.0))
    e2 = float(previous_effects.get("eff.2", 0.0))

    def noise():
        return rng.gauss(0.0, 0.01)

    if body_variant == "A":
        return {
            "rec.0": 0.80 * e0 + noise(),
            "rec.1": 0.80 * e1 + noise(),
            "rec.2": rng.uniform(-0.08, 0.08),
        }
    return {
        "rec.0": 0.70 * e1 + noise(),
        "rec.1": 0.70 * e2 + noise(),
        "rec.2": 0.35 * e0 + noise(),
    }


def _recovery_latency(errors: Sequence[float], target: float, *, window: int = 5) -> int | None:
    if not errors:
        return None
    threshold = max(1e-6, target * 1.20)
    for start in range(0, max(1, len(errors) - window + 1)):
        chunk = errors[start : start + window]
        if len(chunk) == window and sum(chunk) / window <= threshold:
            return start
    return None


def _run_phase(
    ind: Individual,
    *,
    name: str,
    body_variant: str,
    ticks: int,
    rng: random.Random,
    previous_effects: dict[str, float],
    baseline_error: float,
) -> tuple[PhaseResult, dict[str, float]]:
    errors: list[float] = []
    confidences: list[float] = []
    disruptions = 0
    revisions_before = ind.symbiont.body_schema_revision_count
    first_revision_latency: int | None = None
    mapping_before = _mapping_signature(ind)

    effects = dict(previous_effects)
    for local_tick in range(ticks):
        stimuli = _feedback(body_variant=body_variant, previous_effects=effects, rng=rng)
        rec = ind.step(external_stimuli=stimuli)
        effects = {
            port_id: consequence.physical_effect
            for port_id, consequence in rec.physical_consequences.items()
        }
        err = _tick_error(ind)
        errors.append(err)
        confidences.append(float(ind.symbiont.body_schema_confidence))
        disruptions += int(ind.symbiont.body_schema_disrupted)

        if (
            first_revision_latency is None
            and ind.symbiont.body_schema_revision_count > revisions_before
        ):
            first_revision_latency = local_tick

    revisions_after = ind.symbiont.body_schema_revision_count
    mapping_after = _mapping_signature(ind)
    early_n = min(5, len(errors))
    initial_error = sum(errors[:early_n]) / early_n if early_n else 0.0
    final_error = sum(errors[-early_n:]) / early_n if early_n else 0.0
    shock = initial_error - baseline_error

    return (
        PhaseResult(
            name=name,
            mean_prediction_error=sum(errors) / len(errors),
            initial_prediction_error=initial_error,
            final_prediction_error=final_error,
            prediction_shock=shock,
            disruption_ticks=disruptions,
            revision_delta=revisions_after - revisions_before,
            first_revision_latency=first_revision_latency,
            recovery_latency=_recovery_latency(errors, baseline_error),
            mean_schema_confidence=sum(confidences) / len(confidences),
            mapping_before=mapping_before,
            mapping_after=mapping_after,
            mapping_changed=mapping_before != mapping_after,
        ),
        effects,
    )


def _run_seed(seed: int, *, phase_ticks: int) -> CausalRevisionSeedResult:
    rng = random.Random(seed)
    ind = create_individual(
        f"sym-e4-{seed}",
        f"body-a-{seed}",
        num_receptors=3,
        num_effectors=2,
    )
    _stabilize_body(ind.body)
    body_a = ind.body
    original_bindings = dict(ind.session.output_bindings)
    previous_effects: dict[str, float] = {}
    phases: list[PhaseResult] = []

    stable, previous_effects = _run_phase(
        ind,
        name="stable_a",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=0.0,
    )
    phases.append(stable)
    stable_baseline = max(1e-6, stable.final_prediction_error)

    ind.session.permute_outputs(dict(original_bindings))
    sham, previous_effects = _run_phase(
        ind,
        name="sham",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=stable_baseline,
    )
    phases.append(sham)

    keys = sorted(original_bindings)
    permuted = dict(original_bindings)
    if len(keys) >= 2:
        permuted[keys[0]], permuted[keys[1]] = permuted[keys[1]], permuted[keys[0]]
    ind.session.permute_outputs(permuted)
    perm, previous_effects = _run_phase(
        ind,
        name="permutation",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=stable_baseline,
    )
    phases.append(perm)

    ind.session.permute_outputs(dict(original_bindings))
    restored, previous_effects = _run_phase(
        ind,
        name="restored_a",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=stable_baseline,
    )
    phases.append(restored)
    restored_baseline = max(1e-6, restored.final_prediction_error)

    body_a.break_effector("eff.0")
    broken, previous_effects = _run_phase(
        ind,
        name="broken_effector",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=restored_baseline,
    )
    phases.append(broken)

    body_a.repair_effector("eff.0")
    repaired, previous_effects = _run_phase(
        ind,
        name="repaired",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=restored_baseline,
    )
    phases.append(repaired)
    repaired_baseline = max(1e-6, repaired.final_prediction_error)

    body_b = create_standard_body(
        f"body-b-{seed}",
        num_receptors=3,
        num_effectors=3,
        morphology="alternate",
    )
    _stabilize_body(body_b)
    ind.transplant_to(body_b)
    previous_effects = {}
    transplanted, previous_effects = _run_phase(
        ind,
        name="transplant_b",
        body_variant="B",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=repaired_baseline,
    )
    phases.append(transplanted)

    ind.transplant_to(body_a)
    previous_effects = {}
    returned, previous_effects = _run_phase(
        ind,
        name="return_a",
        body_variant="A",
        ticks=phase_ticks,
        rng=rng,
        previous_effects=previous_effects,
        baseline_error=stable_baseline,
    )
    phases.append(returned)

    sham_delta = sham.mean_prediction_error - stable.mean_prediction_error
    perm_delta = perm.mean_prediction_error - stable.mean_prediction_error
    break_delta = broken.mean_prediction_error - restored.mean_prediction_error
    transplant_delta = transplanted.mean_prediction_error - repaired.mean_prediction_error

    real_changes = [abs(perm_delta), abs(break_delta), abs(transplant_delta)]
    sham_specific = abs(sham_delta) < max(real_changes)

    transplant_recovery = transplanted.recovery_latency
    return_recovery = returned.recovery_latency
    return_advantage = return_recovery is not None and (
        transplant_recovery is None or return_recovery < transplant_recovery
    )

    return CausalRevisionSeedResult(
        seed=seed,
        phases=tuple(phases),
        sham_error_delta=sham_delta,
        permutation_error_delta=perm_delta,
        break_error_delta=break_delta,
        transplant_error_delta=transplant_delta,
        permutation_revision=perm.revision_delta > 0,
        break_revision=broken.revision_delta > 0,
        transplant_revision=transplanted.revision_delta > 0,
        permutation_mapping_changed=perm.mapping_changed,
        transplant_mapping_changed=transplanted.mapping_changed,
        return_a_faster_than_transplant=return_advantage,
        sham_quieter_than_real_changes=sham_specific,
    )


def run_causal_revision_sequence_study(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
    steps: int = 320,
) -> CausalRevisionStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 160 or steps > 80_000 or steps % 8:
        raise ValueError("steps must be a multiple of 8 within [160,80000]")
    phase_ticks = steps // 8

    results = tuple(_run_seed(seed, phase_ticks=phase_ticks) for seed in normalized)
    replay = tuple(_run_seed(seed, phase_ticks=phase_ticks) for seed in normalized)

    n = len(results)

    def rate(attr):
        return sum(bool(getattr(x, attr)) for x in results) / n

    perm_rate = rate("permutation_revision")
    break_rate = rate("break_revision")
    transplant_rate = rate("transplant_revision")
    perm_map_rate = rate("permutation_mapping_changed")
    transplant_map_rate = rate("transplant_mapping_changed")
    return_adv_rate = rate("return_a_faster_than_transplant")
    sham_rate = rate("sham_quieter_than_real_changes")
    deterministic = results == replay

    supported = (
        perm_rate >= 0.70
        and break_rate >= 0.70
        and transplant_rate >= 0.70
        and perm_map_rate >= 0.70
        and transplant_map_rate >= 0.70
        and sham_rate >= 0.70
        and deterministic
    )

    return CausalRevisionStudy(
        seeds=normalized,
        phase_ticks=phase_ticks,
        per_seed=results,
        permutation_revision_rate=perm_rate,
        break_revision_rate=break_rate,
        transplant_revision_rate=transplant_rate,
        permutation_mapping_change_rate=perm_map_rate,
        transplant_mapping_change_rate=transplant_map_rate,
        return_a_reacquisition_advantage_rate=return_adv_rate,
        sham_specificity_rate=sham_rate,
        replay_deterministic=deterministic,
        h1_supported=supported,
    )


__all__ = [
    "PhaseResult",
    "CausalRevisionSeedResult",
    "CausalRevisionStudy",
    "run_causal_revision_sequence_study",
]
