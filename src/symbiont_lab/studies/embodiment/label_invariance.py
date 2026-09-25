"""E8 adversarial integrity study: evaluator/body label invariance.

Two levels are tested:
1. direct canonical Body implantation with renamed physical port labels but
   identical ordinals/mechanics;
2. paired canonical clean Worlds with identical laws and seeds but renamed
   world/resource/hazard identifiers.

Any divergence at level 2 identifies apparatus identity leaking into physical
trajectory rather than a cognitive effect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.core.body import Body, BodyPhysiology, EffectorPort, ReceptorPort
from symbiont.core.individual import Individual
from symbiont.core.symbiont import Symbiont

from symbiont.core.embodiment import implant_body
from symbiont_lab.world.population import PopulationGenesisRuntime
from symbiont_world.genesis import GroundTruth
from symbiont_world.laws import HazardLaw, ResourceLaw
from symbiont_world.topology import HexCoord, HexTopology

_STUDY_ID = "embodiment.label-invariance"


@dataclass(frozen=True, slots=True)
class LabelInvarianceSeedResult:
    seed: int
    port_opaque_inputs_equal: bool
    port_activations_equal: bool
    port_internal_state_equal: bool
    world_trajectory_equal: bool
    first_world_divergence_tick: int | None

    @property
    def all_equal(self) -> bool:
        return (
            self.port_opaque_inputs_equal
            and self.port_activations_equal
            and self.port_internal_state_equal
            and self.world_trajectory_equal
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
    port_invariant_rate: float
    world_invariant_rate: float
    invariant_rate: float
    replay_deterministic: bool
    integrity_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [x.as_dict() for x in self.per_seed],
            "port_invariant_rate": self.port_invariant_rate,
            "world_invariant_rate": self.world_invariant_rate,
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
        basal_metabolic_rate=0.001,
        degradation_rate=0.00005,
    )


def _subject_snapshot(ind: Individual) -> tuple:
    sym = ind.symbiont
    return (
        sym.agency_snapshot(),
        tuple(
            sorted(
                (
                    item.effect_id,
                    item.competence_id,
                    round(float(item.confidence), 12),
                    round(float(item.reliability), 12),
                )
                for item in sym.controllability_model.estimates
            )
        ),
        sym.body_schema.self_caused_channels,
        sym.body_schema.somatic_correlated_channels,
        sym.body_schema.external_channels,
        round(float(sym.body_schema_confidence), 12),
        sym.body_schema_revision_count,
        round(float(sym.body_schema.boundary_disruption_score), 12),
        sym.self_model.ticks_experienced,
        round(float(sym.self_model.historical_stability), 12),
        round(float(sym.self_model.integrity_confidence), 12),
    )


def _port_label_assay(seed: int, *, steps: int) -> tuple[bool, bool, bool]:
    body_a = _make_body(f"body-a-{seed}", renamed=False)
    body_b = _make_body(f"body-b-{seed}", renamed=True)

    sym_a = Symbiont(f"sym-e8-{seed}", seed=seed)
    sym_b = Symbiont(f"sym-e8-{seed}", seed=seed)

    ind_a = Individual(sym_a, body_a, implant_body(sym_a.symbiont_id, body_a))
    ind_b = Individual(sym_b, body_b, implant_body(sym_b.symbiont_id, body_b))

    inputs_equal = True
    activations_equal = True

    for tick in range(steps):
        values = (
            ((tick * 17 + seed) % 101) / 100.0,
            ((tick * 29 + seed * 3) % 101) / 100.0,
            ((tick * 43 + seed * 5) % 101) / 100.0,
        )
        ra = ind_a.step({"rec.0": values[0], "rec.1": values[1], "rec.2": values[2]})
        rb = ind_b.step({"alpha": values[0], "beta": values[1], "gamma": values[2]})
        inputs_equal &= ra.opaque_inputs == rb.opaque_inputs
        activations_equal &= ra.opaque_activations == rb.opaque_activations

    return inputs_equal, activations_equal, _subject_snapshot(ind_a) == _subject_snapshot(ind_b)


def _renamed_truth(*, renamed: bool) -> GroundTruth:
    resource_id = "resource.display.beta" if renamed else "resource.display.alpha"
    hazard_id = "hazard.display.beta" if renamed else "hazard.display.alpha"
    return GroundTruth(
        fields={},
        resources={
            resource_id: ResourceLaw(
                capacity=1.0,
                renewal_rate=0.01,
                decay_rate=0.0,
                initial_quantity=0.8,
            )
        },
        hazards={
            hazard_id: HazardLaw(
                base_probability=0.03,
                density_coupling=0.0,
            )
        },
    )


def _world_subject_trace(pop: PopulationGenesisRuntime, organism_id: str) -> tuple:
    rig = pop._rigs[organism_id]
    ind = rig.individual
    assert ind is not None
    last = ind.history[-1] if ind.history else None
    return (
        tuple(sorted(last.opaque_inputs.items())) if last else (),
        tuple(sorted(last.opaque_activations.items())) if last else (),
        _subject_snapshot(ind),
        ind.body.physiology.energy_reserve,
        ind.body.physiology.structural_integrity,
        pop.state.bodies[organism_id].occupied_cell.q,
        pop.state.bodies[organism_id].occupied_cell.r,
    )


def _world_label_assay(seed: int, *, steps: int) -> tuple[bool, int | None]:
    organism_id = f"e8-subject-{seed}"
    a = PopulationGenesisRuntime(
        ground_truth=_renamed_truth(renamed=False),
        world_id=f"world-display-alpha-{seed}",
        organism_ids=(organism_id,),
        world_seed=seed,
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )
    b = PopulationGenesisRuntime(
        ground_truth=_renamed_truth(renamed=True),
        world_id=f"world-display-beta-{seed}",
        organism_ids=(organism_id,),
        world_seed=seed,
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )

    for tick in range(steps):
        a.run_tick()
        b.run_tick()
        if _world_subject_trace(a, organism_id) != _world_subject_trace(b, organism_id):
            return False, tick
    return True, None


def _run_seed(seed: int, *, steps: int) -> LabelInvarianceSeedResult:
    pi, pa, ps = _port_label_assay(seed, steps=steps)
    world_equal, first_divergence = _world_label_assay(seed, steps=steps)
    return LabelInvarianceSeedResult(
        seed=seed,
        port_opaque_inputs_equal=pi,
        port_activations_equal=pa,
        port_internal_state_equal=ps,
        world_trajectory_equal=world_equal,
        first_world_divergence_tick=first_divergence,
    )


def run_label_invariance_study(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
    steps: int = 300,
) -> LabelInvarianceStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 20 or steps > 10_000:
        raise ValueError("steps must be within [20,10000]")

    results = tuple(_run_seed(s, steps=steps) for s in normalized)
    replay = tuple(_run_seed(s, steps=steps) for s in normalized)

    port_rate = sum(
        x.port_opaque_inputs_equal and x.port_activations_equal and x.port_internal_state_equal
        for x in results
    ) / len(results)
    world_rate = sum(x.world_trajectory_equal for x in results) / len(results)
    total_rate = sum(x.all_equal for x in results) / len(results)
    deterministic = results == replay

    return LabelInvarianceStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        port_invariant_rate=port_rate,
        world_invariant_rate=world_rate,
        invariant_rate=total_rate,
        replay_deterministic=deterministic,
        integrity_pass=(total_rate == 1.0 and deterministic),
    )


__all__ = [
    "LabelInvarianceSeedResult",
    "LabelInvarianceStudy",
    "run_label_invariance_study",
]
