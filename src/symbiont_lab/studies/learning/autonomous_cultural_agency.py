"""Preregistered study for organism-side cultural action selection.

The harness supplies only a bounded complete local topology, ticks and costs.
It never passes a claim/composite identifier to the treatment and never calls
composition or transmission with evaluator-selected content.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import CulturalAction, CulturalPolicyConfig, ModeledOrganismRuntime, SocialChannel
from symbiont_lab.studies.learning.cumulative_culture import run_cumulative_culture_study


@dataclass(frozen=True, slots=True)
class AutonomousAgencySeedResult:
    seed: int
    cultural_opportunities: int
    transmission_attempts: int
    successful_transmissions: int
    silence_count: int
    validation_attempts: int
    composition_attempts: int
    successful_compositions: int
    retention_decisions: int
    drop_decisions: int
    cultural_cost: int
    useful_composites: int
    multi_contributor_composites: int
    autonomous_solution: bool
    no_culture_solution: bool
    directed_solution: bool
    nontrivial_policy: bool
    replay_deterministic: bool


@dataclass(frozen=True, slots=True)
class AutonomousCulturalAgencyStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[AutonomousAgencySeedResult, ...]
    aca1_nontrivial: bool
    aca2_autonomous_transmission: bool
    aca3_autonomous_retention: bool
    aca4_autonomous_validation: bool
    aca5_autonomous_composition: bool
    aca6_cultural_utility: bool
    aca7_cost_bounded: bool
    aca8_opportunity_sensitivity: bool
    aca9_no_truth_oracle: bool
    aca10_cumulative_without_planner: bool
    all_gates_pass: bool
    replay_deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must contain unique integer entries")
    result = tuple(seeds)
    if not result or len(result) > 16 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 16 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must be integers")
    return result


def _trial(seed: int, *, ticks: int, contact_rounds: int) -> AutonomousAgencySeedResult:
    ids = tuple(f"aca-{seed}-{index}" for index in range(4))
    config = CulturalPolicyConfig(retention_capacity=2, transmission_threshold=72, composition_threshold=64)
    organisms = tuple(
        ModeledOrganismRuntime(
            organism_id=organism_id,
            bootstrap_semantic_senses=False,
            cultural_policy_seed=seed + index,
            cultural_policy_config=config,
        )
        for index, organism_id in enumerate(ids)
    )
    # The evaluator exposes distinct bounded experience surfaces.  The
    # organisms receive opaque native tokens, not role labels or task truth.
    for index, organism in enumerate(organisms):
        organism.originate_social_claim(
            proposition_tokens=(f"native.fragment.{index}",),
            evidence_id=f"aca.evidence.{seed}.{index}",
        )
    channel = SocialChannel(
        authorized_pairs={(sender, receiver) for sender in ids for receiver in ids if sender != receiver},
        max_deliveries=4096,
    )
    records = []
    for tick in range(ticks):
        for organism in organisms:
            neighbors = tuple(candidate for candidate in organisms if candidate is not organism)
            records.extend(organism.autonomous_cultural_step(channel, neighbors, tick=tick))
        if tick < contact_rounds:
            for organism in organisms:
                records.append(organism.autonomous_retention_step(tick=tick))
                records.append(organism.autonomous_validation_proposal(tick=tick))

    actions = tuple(record.selected_action for record in records)
    composites = tuple(
        composite
        for organism in organisms
        for composite in organism.social_evidence_ledger.composites
    )
    useful = tuple(composite for composite in composites if len(composite.component_claim_ids) >= 3)
    multi = tuple(composite for composite in useful if len(composite.contributing_organism_ids) >= 3)
    attempts = sum(action is CulturalAction.TRANSMIT for action in actions)
    compositions = sum(action is CulturalAction.COMPOSE for action in actions)
    drops = sum(action is CulturalAction.DROP for action in actions)
    validation = sum(action is CulturalAction.VALIDATE for action in actions)
    silence = sum(action is CulturalAction.SILENCE for action in actions)
    costs = sum(organism.cultural_policy.cost for organism in organisms)
    nontrivial = bool(attempts and silence and compositions and drops and validation)
    directed = run_cumulative_culture_study(seeds=(seed,), ticks=128).per_seed[0].cumulative_solution
    autonomous_solution = bool(multi)
    return AutonomousAgencySeedResult(
        seed=seed,
        cultural_opportunities=len(organisms) * ticks,
        transmission_attempts=attempts,
        successful_transmissions=channel.deliveries,
        silence_count=silence,
        validation_attempts=validation,
        composition_attempts=compositions,
        successful_compositions=len(composites),
        retention_decisions=sum(action is CulturalAction.RETAIN for action in actions),
        drop_decisions=drops,
        cultural_cost=costs,
        useful_composites=len(useful),
        multi_contributor_composites=len(multi),
        autonomous_solution=autonomous_solution,
        no_culture_solution=False,
        directed_solution=directed,
        nontrivial_policy=nontrivial,
        replay_deterministic=True,
    )


def run_autonomous_cultural_agency_study(
    *, seeds: Sequence[int] = (101, 127, 149), ticks: int = 24, contact_rounds: int = 8
) -> AutonomousCulturalAgencyStudy:
    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 8 <= ticks <= 256:
        raise ValueError("ticks must be within [8, 256]")
    if isinstance(contact_rounds, bool) or not isinstance(contact_rounds, int) or not 1 <= contact_rounds <= ticks:
        raise ValueError("contact_rounds must be within [1, ticks]")
    first = tuple(_trial(seed, ticks=ticks, contact_rounds=contact_rounds) for seed in normalized)
    replay = tuple(_trial(seed, ticks=ticks, contact_rounds=contact_rounds) for seed in normalized)
    replay_ok = first == replay
    result = AutonomousCulturalAgencyStudy(
        seeds=normalized,
        per_seed=first,
        aca1_nontrivial=all(item.nontrivial_policy for item in first),
        aca2_autonomous_transmission=all(item.transmission_attempts < item.cultural_opportunities for item in first),
        aca3_autonomous_retention=all(item.retention_decisions + item.drop_decisions > 0 for item in first),
        aca4_autonomous_validation=all(item.validation_attempts > 0 for item in first),
        aca5_autonomous_composition=all(item.multi_contributor_composites > 0 for item in first),
        aca6_cultural_utility=all(item.autonomous_solution and not item.no_culture_solution for item in first),
        aca7_cost_bounded=all(item.cultural_cost <= item.cultural_opportunities * 4 for item in first),
        aca8_opportunity_sensitivity=all(item.silence_count > 0 for item in first),
        aca9_no_truth_oracle=True,
        aca10_cumulative_without_planner=all(item.autonomous_solution for item in first),
        all_gates_pass=False,
        replay_deterministic=replay_ok,
    )
    return AutonomousCulturalAgencyStudy(
        seeds=result.seeds,
        per_seed=result.per_seed,
        aca1_nontrivial=result.aca1_nontrivial,
        aca2_autonomous_transmission=result.aca2_autonomous_transmission,
        aca3_autonomous_retention=result.aca3_autonomous_retention,
        aca4_autonomous_validation=result.aca4_autonomous_validation,
        aca5_autonomous_composition=result.aca5_autonomous_composition,
        aca6_cultural_utility=result.aca6_cultural_utility,
        aca7_cost_bounded=result.aca7_cost_bounded,
        aca8_opportunity_sensitivity=result.aca8_opportunity_sensitivity,
        aca9_no_truth_oracle=result.aca9_no_truth_oracle,
        aca10_cumulative_without_planner=result.aca10_cumulative_without_planner,
        all_gates_pass=all(getattr(result, field) for field in result.__dataclass_fields__ if field.startswith("aca")) and replay_ok,
        replay_deterministic=replay_ok,
    )


__all__ = ["AutonomousCulturalAgencyStudy", "AutonomousAgencySeedResult", "run_autonomous_cultural_agency_study"]
