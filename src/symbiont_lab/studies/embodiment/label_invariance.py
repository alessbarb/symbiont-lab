"""E8 adversarial integrity study: evaluator/body label invariance.

Physically identical bodies are constructed with different human-readable port
labels but identical physical ordinals and mechanics. The subject-visible
opaque trajectory must be identical when using the canonical implant_body path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.core.body import Body, BodyPhysiology, EffectorPort, ReceptorPort
from symbiont.core.embodiment import implant_body
from symbiont.core.individual import Individual
from symbiont.core.symbiont import Symbiont

_STUDY_ID = "embodiment.label-invariance"


@dataclass(frozen=True, slots=True)
class LabelInvarianceSeedResult:
    seed: int
    opaque_inputs_equal: bool
    activations_equal: bool
    agency_equal: bool
    body_schema_equal: bool
    self_model_equal: bool

    @property
    def all_equal(self) -> bool:
        return (
            self.opaque_inputs_equal
            and self.activations_equal
            and self.agency_equal
            and self.body_schema_equal
            and self.self_model_equal
        )

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["all_equal"] = self.all_equal
        return data


@dataclass(frozen=True, slots=True)
class LabelInvarianceStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[LabelInvarianceSeedResult, ...]
    invariant_rate: float
    replay_deterministic: bool
    integrity_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [x.as_dict() for x in self.per_seed],
            "invariant_rate": self.invariant_rate,
            "replay_deterministic": self.replay_deterministic,
            "integrity_pass": self.integrity_pass,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    result = tuple(seeds)
    if not result or len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(s, bool) or not isinstance(s, int) for s in result):
        raise ValueError("seeds must contain integers only")
    return result


def _make_body(body_id: str, *, renamed: bool) -> Body:
    physiology = BodyPhysiology(
        energy_reserve=5.0,
        max_energy=5.0,
        basal_metabolic_rate=0.001,
        degradation_rate=0.00005,
    )
    rnames = ("alpha", "beta", "gamma") if renamed else ("rec.0", "rec.1", "rec.2")
    enames = ("motor.zeta", "motor.eta") if renamed else ("eff.0", "eff.1")
    receptors = [
        ReceptorPort(port_id=name, kind="opaque-physical", ordinal=i)
        for i, name in enumerate(rnames)
    ]
    effectors = [
        EffectorPort(
            port_id=name,
            kind="impulse",
            ordinal=i,
            direction=i,
            efficiency=1.0,
            cost_per_activation=0.001,
        )
        for i, name in enumerate(enames)
    ]
    return Body(
        body_id,
        morphology_name="same-physics",
        receptors=receptors,
        effectors=effectors,
        physiology=physiology,
    )


def _snapshot(ind: Individual) -> tuple:
    sym = ind.symbiont
    agency = tuple(sorted(sym.agency_model.agency_confidence.items()))
    controllability = tuple(sorted(sym.agency_model.controllability.items()))
    schema = (
        tuple(sorted(sym.body_schema.self_caused_channels)),
        tuple(sorted(sym.body_schema.somatic_correlated_channels)),
        tuple(sorted(sym.body_schema.internal_channels)),
        tuple(sorted(sym.body_schema.external_channels)),
        sym.body_schema.overall_confidence,
        sym.body_schema.revision_count,
    )
    self_model = (
        sym.self_model.ticks_experienced,
        sym.self_model.historical_stability,
        sym.self_model.integrity_confidence,
    )
    return agency, controllability, schema, self_model


def _run_seed(seed: int, *, steps: int) -> LabelInvarianceSeedResult:
    body_a = _make_body(f"body-a-{seed}", renamed=False)
    body_b = _make_body(f"body-b-{seed}", renamed=True)

    sym_a = Symbiont(f"sym-e8-{seed}", seed=seed)
    sym_b = Symbiont(f"sym-e8-{seed}", seed=seed)

    ind_a = Individual(sym_a, body_a, implant_body(sym_a.symbiont_id, body_a))
    ind_b = Individual(sym_b, body_b, implant_body(sym_b.symbiont_id, body_b))

    inputs_equal = True
    activations_equal = True

    for tick in range(steps):
        # Same physical field by structural ordinal, with different apparatus labels.
        values = (
            ((tick * 17 + seed) % 101) / 100.0,
            ((tick * 29 + seed * 3) % 101) / 100.0,
            ((tick * 43 + seed * 5) % 101) / 100.0,
        )
        stim_a = {"rec.0": values[0], "rec.1": values[1], "rec.2": values[2]}
        stim_b = {"alpha": values[0], "beta": values[1], "gamma": values[2]}

        ra = ind_a.step(stim_a)
        rb = ind_b.step(stim_b)

        inputs_equal &= ra.opaque_inputs == rb.opaque_inputs
        activations_equal &= ra.opaque_activations == rb.opaque_activations

    sa = _snapshot(ind_a)
    sb = _snapshot(ind_b)

    return LabelInvarianceSeedResult(
        seed=seed,
        opaque_inputs_equal=inputs_equal,
        activations_equal=activations_equal,
        agency_equal=sa[:2] == sb[:2],
        body_schema_equal=sa[2] == sb[2],
        self_model_equal=sa[3] == sb[3],
    )


def run_label_invariance_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
    steps: int = 300,
) -> LabelInvarianceStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 20 or steps > 100_000:
        raise ValueError("steps must be within [20,100000]")
    results = tuple(_run_seed(s, steps=steps) for s in normalized)
    replay = tuple(_run_seed(s, steps=steps) for s in normalized)
    rate = sum(x.all_equal for x in results) / len(results)
    deterministic = results == replay
    return LabelInvarianceStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        invariant_rate=rate,
        replay_deterministic=deterministic,
        integrity_pass=(rate == 1.0 and deterministic),
    )
