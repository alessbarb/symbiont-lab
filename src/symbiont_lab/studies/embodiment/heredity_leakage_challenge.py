"""E7 adversarial inheritance leakage challenge.

The study has two layers:

1. Birth integrity: learned parent sensorimotor/agency/body-schema/perceptual
   state must not cross reproduction.
2. Transformed-offspring challenge: inherited predisposition is tested under
   same, permuted, renamed, expanded-morphology and reversed-correlation
   conditions. A lawful inherited learning-rate modulation may change learning
   speed, but no child may start with mapping-specific knowledge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    SymbiontGenome,
    create_germline_state,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.symbiont import Symbiont

_STUDY_ID = "embodiment.heredity-leakage-challenge"


@dataclass(frozen=True, slots=True)
class OffspringConditionResult:
    condition: str
    inherited_learning_rate: float
    control_learning_rate: float
    inherited_initial_weight: float
    control_initial_weight: float
    inherited_final_abs_error: float
    control_final_abs_error: float
    inherited_final_weight: float
    control_final_weight: float
    zero_shot_mapping_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HeredityLeakSeedResult:
    seed: int
    package_has_only_legitimate_payload: bool
    child_sensorimotor_empty: bool
    child_agency_empty: bool
    child_body_schema_empty: bool
    child_perceptual_empty: bool
    epigenetic_mark_transmitted_or_lawfully_dropped: bool
    phenotype_expression_matches_package: bool
    transformed_conditions: tuple[OffspringConditionResult, ...]

    @property
    def no_leak(self) -> bool:
        return (
            self.package_has_only_legitimate_payload
            and self.child_sensorimotor_empty
            and self.child_agency_empty
            and self.child_body_schema_empty
            and self.child_perceptual_empty
            and self.epigenetic_mark_transmitted_or_lawfully_dropped
            and self.phenotype_expression_matches_package
            and all(item.zero_shot_mapping_equal for item in self.transformed_conditions)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "package_has_only_legitimate_payload": self.package_has_only_legitimate_payload,
            "child_sensorimotor_empty": self.child_sensorimotor_empty,
            "child_agency_empty": self.child_agency_empty,
            "child_body_schema_empty": self.child_body_schema_empty,
            "child_perceptual_empty": self.child_perceptual_empty,
            "epigenetic_mark_transmitted_or_lawfully_dropped": self.epigenetic_mark_transmitted_or_lawfully_dropped,
            "phenotype_expression_matches_package": self.phenotype_expression_matches_package,
            "transformed_conditions": [item.as_dict() for item in self.transformed_conditions],
            "no_leak": self.no_leak,
        }


@dataclass(frozen=True, slots=True)
class HeredityLeakageStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[HeredityLeakSeedResult, ...]
    no_leak_rate: float
    zero_shot_mapping_invariance_rate: float
    phenotypic_expression_rate: float
    replay_deterministic: bool
    integrity_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "per_seed": [x.as_dict() for x in self.per_seed],
            "no_leak_rate": self.no_leak_rate,
            "zero_shot_mapping_invariance_rate": self.zero_shot_mapping_invariance_rate,
            "phenotypic_expression_rate": self.phenotypic_expression_rate,
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


def _control_germline(genome: SymbiontGenome) -> GermlineState:
    return GermlineState(birth_expression=dict(genome.loci_values))


def _child_from_package(
    package: InheritancePackage,
    *,
    seed: int,
    inherited_marks: bool,
    suffix: str,
) -> Symbiont:
    germline = create_germline_state(
        package.genome,
        epigenetic_marks=(package.epigenetic_marks if inherited_marks else ()),
    )
    return Symbiont(
        f"child-{suffix}-{seed}",
        seed=seed,
        genome=package.genome,
        germline=germline,
    )


def _learning_assay(
    child: Symbiont,
    *,
    condition: str,
    ticks: int = 80,
) -> tuple[float, float, float]:
    """Return initial relation weight, final prediction error, final weight.

    This observer-side assay exercises the canonical low-level dynamics model
    through its opaque interface. No body semantics or inherited mapping is
    supplied.
    """
    model = child.sensorimotor_model

    if condition == "same":
        out_ch, target_ch, sign, extra_inputs = "out.0", "in.0", 1.0, ()
    elif condition == "permuted":
        out_ch, target_ch, sign, extra_inputs = "out.0", "in.1", 1.0, ("in.0",)
    elif condition == "renamed":
        out_ch, target_ch, sign, extra_inputs = "out.x7", "in.q3", 1.0, ()
    elif condition == "expanded_morphology":
        out_ch, target_ch, sign, extra_inputs = (
            "out.2",
            "in.4",
            1.0,
            (
                "in.0",
                "in.1",
                "in.2",
                "in.3",
                "in.5",
            ),
        )
    elif condition == "reversed":
        out_ch, target_ch, sign, extra_inputs = "out.0", "in.0", -1.0, ()
    else:
        raise ValueError(f"unknown condition {condition}")

    initial = model.relation_weight(out_ch, target_ch)
    final_error = 0.0

    for tick in range(ticks):
        act = 0.0 if tick % 4 == 0 else 0.65
        actual = sign * 0.45 * act
        in_channels = (target_ch,) + tuple(extra_inputs)
        model.predict({out_ch: act}, in_channels)

        deltas = {target_ch: actual}
        for index, decoy in enumerate(extra_inputs):
            deltas[decoy] = ((tick + index * 3) % 9 - 4) * 0.005

        residuals = model.observe(deltas, tick=tick + 1)
        final_error = next(
            (float(item.error) for item in residuals if item.percept_id == target_ch),
            0.0,
        )

    return (
        initial,
        abs(final_error),
        model.relation_weight(out_ch, target_ch),
    )


def _run_transformed_conditions(
    package: InheritancePackage,
    *,
    seed: int,
) -> tuple[OffspringConditionResult, ...]:
    results: list[OffspringConditionResult] = []
    for index, condition in enumerate(
        ("same", "permuted", "renamed", "expanded_morphology", "reversed")
    ):
        inherited = _child_from_package(
            package,
            seed=seed + 1000 + index,
            inherited_marks=True,
            suffix=f"inherited-{condition}",
        )
        control = _child_from_package(
            package,
            seed=seed + 1000 + index,
            inherited_marks=False,
            suffix=f"control-{condition}",
        )

        inherited_initial, inherited_error, inherited_weight = _learning_assay(
            inherited, condition=condition
        )
        control_initial, control_error, control_weight = _learning_assay(
            control, condition=condition
        )

        results.append(
            OffspringConditionResult(
                condition=condition,
                inherited_learning_rate=inherited.learning_rate,
                control_learning_rate=control.learning_rate,
                inherited_initial_weight=inherited_initial,
                control_initial_weight=control_initial,
                inherited_final_abs_error=inherited_error,
                control_final_abs_error=control_error,
                inherited_final_weight=inherited_weight,
                control_final_weight=control_weight,
                # Neither inherited nor control child may begin with a
                # mapping-specific sensorimotor solution.
                zero_shot_mapping_equal=(inherited_initial == 0.0 and control_initial == 0.0),
            )
        )
    return tuple(results)


def _run_seed(seed: int) -> HeredityLeakSeedResult:
    base = create_standard_genome(f"parent-{seed}")
    # Make transmission deterministic for the integrity assay while keeping the
    # inherited content a legitimate capacity parameter.
    genome = SymbiontGenome(
        genome_id=base.genome_id,
        loci_values={
            **dict(base.loci_values),
            "learning_rate": 0.12,
            "acquired_transmission_rate": 1.0,
            "epigenetic_decay": 0.20,
        },
        specs=base.specs,
    )
    germline = create_germline_state(genome)
    mark = EpigeneticMark(
        locus="learning_rate",
        delta=0.08,
        strength=1.0,
        generations_left=3,
    )
    assert germline.add_mark(mark)

    parent = Symbiont(
        f"parent-sym-{seed}",
        seed=seed,
        genome=genome,
        germline=germline,
    )

    # Deliberately create concrete parent lifetime state through the real
    # canonical Symbiont path. None of it may cross birth.
    parent.register_output_channels(("out.parent_specific",))
    for tick in range(80):
        previous_act = parent.last_activations.get("out.parent_specific", 0.0)
        parent.step(
            {
                "in.parent_specific": 0.4 * previous_act + (tick % 5) * 0.001,
                "in.body_specific": 0.2 * previous_act + (tick % 7) * 0.001,
            }
        )

    package = create_offspring_package(
        genome,
        germline,
        seed=seed,
        generation=1,
    )

    child_germline = create_germline_state(
        package.genome,
        epigenetic_marks=package.epigenetic_marks,
    )
    child = Symbiont(
        f"child-sym-{seed}",
        seed=seed + 10000,
        genome=package.genome,
        germline=child_germline,
    )

    payload_ok = (
        bool(tuple(package.parent_ids))
        and not hasattr(package, "body_schema")
        and not hasattr(package, "agency_model")
        and not hasattr(package, "sensorimotor_model")
        and not hasattr(package, "memories")
    )
    sm_empty = child.sensorimotor_model.relation_count == 0 and child.causal_evidence.evidence == ()
    agency_empty = (
        child.agency_model.estimates == () and child.controllability_model.estimates == ()
    )
    schema_empty = (
        child.body_schema.self_caused_channels == ()
        and child.body_schema.somatic_correlated_channels == ()
        and child.body_schema.external_channels == ()
        and child.body_schema.boundary_confidence == 0.0
    )
    perceptual_empty = (
        child.effect_space.effects == () and child.competence_effect_model.context_count == 0
    )

    transmitted = {m.locus: m for m in package.epigenetic_marks}
    epi_ok = set(transmitted) <= {"learning_rate"}
    expected_lr = child_germline.effective_expression(
        "learning_rate",
        float(package.genome.get("learning_rate")),
        spec=package.genome.specs["learning_rate"],
    )
    expression_ok = abs(child.learning_rate - expected_lr) <= 1e-12

    transformed = _run_transformed_conditions(package, seed=seed)

    return HeredityLeakSeedResult(
        seed=seed,
        package_has_only_legitimate_payload=payload_ok,
        child_sensorimotor_empty=sm_empty,
        child_agency_empty=agency_empty,
        child_body_schema_empty=schema_empty,
        child_perceptual_empty=perceptual_empty,
        epigenetic_mark_transmitted_or_lawfully_dropped=epi_ok,
        phenotype_expression_matches_package=expression_ok,
        transformed_conditions=transformed,
    )


def run_heredity_leakage_challenge_study(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
) -> HeredityLeakageStudy:
    normalized = _normalize_seeds(seeds)
    results = tuple(_run_seed(s) for s in normalized)
    replay = tuple(_run_seed(s) for s in normalized)

    no_leak_rate = sum(x.no_leak for x in results) / len(results)
    transformed = [c for x in results for c in x.transformed_conditions]
    zero_shot_rate = sum(c.zero_shot_mapping_equal for c in transformed) / len(transformed)
    expression_rate = sum(x.phenotype_expression_matches_package for x in results) / len(results)
    deterministic = results == replay

    return HeredityLeakageStudy(
        seeds=normalized,
        per_seed=results,
        no_leak_rate=no_leak_rate,
        zero_shot_mapping_invariance_rate=zero_shot_rate,
        phenotypic_expression_rate=expression_rate,
        replay_deterministic=deterministic,
        integrity_pass=(
            no_leak_rate == 1.0
            and zero_shot_rate == 1.0
            and expression_rate == 1.0
            and deterministic
        ),
    )


__all__ = [
    "OffspringConditionResult",
    "HeredityLeakSeedResult",
    "HeredityLeakageStudy",
    "run_heredity_leakage_challenge_study",
]
