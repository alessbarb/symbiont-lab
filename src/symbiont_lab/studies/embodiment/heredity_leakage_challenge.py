"""E7 adversarial inheritance leakage challenge.

A parent is deliberately given learned sensorimotor/agency/body-schema state.
Only SymbiontGenome + legitimate GermlineState may cross reproduction. The
offspring must begin without learned mappings, concepts, body schema or agency
evidence even when a lawful epigenetic mark is transmitted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.symbiont import Symbiont

_STUDY_ID = "embodiment.heredity-leakage-challenge"


@dataclass(frozen=True, slots=True)
class HeredityLeakSeedResult:
    seed: int
    package_has_only_legitimate_payload: bool
    child_sensorimotor_empty: bool
    child_agency_empty: bool
    child_body_schema_empty: bool
    child_perceptual_empty: bool
    epigenetic_mark_transmitted_or_lawfully_dropped: bool

    @property
    def no_leak(self) -> bool:
        return (
            self.package_has_only_legitimate_payload
            and self.child_sensorimotor_empty
            and self.child_agency_empty
            and self.child_body_schema_empty
            and self.child_perceptual_empty
            and self.epigenetic_mark_transmitted_or_lawfully_dropped
        )

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["no_leak"] = self.no_leak
        return data


@dataclass(frozen=True, slots=True)
class HeredityLeakageStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[HeredityLeakSeedResult, ...]
    no_leak_rate: float
    replay_deterministic: bool
    integrity_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "per_seed": [x.as_dict() for x in self.per_seed],
            "no_leak_rate": self.no_leak_rate,
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


def _run_seed(seed: int) -> HeredityLeakSeedResult:
    genome = create_standard_genome(f"parent-{seed}")
    germline = GermlineState(birth_expression=dict(genome.loci_values))

    # Legitimate acquired modulation of a declared regulable capacity.
    mark = EpigeneticMark(
        locus="initial_concepts",
        delta=1.0,
        strength=0.5,
        generations_left=3,
    )
    germline.add_mark(mark)

    parent = Symbiont(f"parent-sym-{seed}", seed=seed, genome=genome, germline=germline)

    # Deliberately contaminate the parent's learned lifetime state with strong,
    # concrete mappings. None of this may cross the germline.
    for tick in range(80):
        act = 0.8 if tick % 3 else 0.0
        parent.perceptual_structure.observe({
            "in.parent_specific": (tick % 11) / 10.0,
            "in.body_specific": (tick % 7) / 6.0,
        })
        parent.agency_model.record_step(
            {"out.parent_specific": act},
            {"in.parent_specific": 0.4 * act, "in.body_specific": 0.2 * act},
        )
        parent.sensorimotor_model.predict_deltas(
            {"out.parent_specific": act},
            ("in.parent_specific", "in.body_specific"),
        )
        parent.sensorimotor_model.update(
            {"in.parent_specific": 0.4 * act, "in.body_specific": 0.2 * act},
            {"out.parent_specific": act},
        )
        parent.body_schema.update_from_agency(
            parent.agency_model,
            parent.perceptual_structure,
        )

    package = create_offspring_package(
        genome,
        germline,
        seed=seed,
        generation=1,
    )

    child_germline = GermlineState(
        birth_expression=dict(package.genome.loci_values),
        acquired_marks={m.locus: m for m in package.epigenetic_marks},
    )
    child = Symbiont(
        f"child-sym-{seed}",
        seed=seed + 10000,
        genome=package.genome,
        germline=child_germline,
    )

    payload_ok = (
        tuple(package.parent_ids)
        and not hasattr(package, "body_schema")
        and not hasattr(package, "agency_model")
        and not hasattr(package, "sensorimotor_model")
        and not hasattr(package, "memories")
    )
    sm_empty = (
        child.sensorimotor_model.weights == {}
        and child.sensorimotor_model.last_predictions == {}
        and child.sensorimotor_model.prediction_errors == {}
    )
    agency_empty = (
        child.agency_model.contingency == {}
        and child.agency_model.controllability == {}
        and child.agency_model.agency_confidence == {}
    )
    schema_empty = (
        child.body_schema.internal_channels == set()
        and child.body_schema.self_caused_channels == set()
        and child.body_schema.somatic_correlated_channels == set()
        and child.body_schema.regions == []
    )
    perceptual_empty = (
        child.perceptual_structure.channel_stats == {}
        and child.perceptual_structure.cross_cov == {}
    )
    transmitted_loci = {m.locus for m in package.epigenetic_marks}
    epi_ok = transmitted_loci <= {"initial_concepts"}

    return HeredityLeakSeedResult(
        seed=seed,
        package_has_only_legitimate_payload=bool(payload_ok),
        child_sensorimotor_empty=sm_empty,
        child_agency_empty=agency_empty,
        child_body_schema_empty=schema_empty,
        child_perceptual_empty=perceptual_empty,
        epigenetic_mark_transmitted_or_lawfully_dropped=epi_ok,
    )


def run_heredity_leakage_challenge_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
) -> HeredityLeakageStudy:
    normalized = _normalize_seeds(seeds)
    results = tuple(_run_seed(s) for s in normalized)
    replay = tuple(_run_seed(s) for s in normalized)
    rate = sum(x.no_leak for x in results) / len(results)
    deterministic = results == replay
    return HeredityLeakageStudy(
        seeds=normalized,
        per_seed=results,
        no_leak_rate=rate,
        replay_deterministic=deterministic,
        integrity_pass=(rate == 1.0 and deterministic),
    )
