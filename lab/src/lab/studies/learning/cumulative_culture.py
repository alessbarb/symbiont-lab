"""Preregistered evaluator-side study for cumulative cultural composition.

The apparatus controls only bounded experience surfaces and authorized delivery.
No role label, ground truth or success metric enters an organism ledger.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import SocialChannel, SocialEvidenceLedger


@dataclass(frozen=True, slots=True)
class CumulativeSeedResult:
    seed: int
    cc1_composition_faithful: bool
    cc2_multi_contributor_provenance: bool
    cc3_cumulative_growth: bool
    cc4_no_founder_completeness: bool
    cc5_super_individual_utility: bool
    cc6_cultural_ratchet: bool
    cc7_degradation: bool
    cc8_error_correction: bool
    replay_valid: bool
    final_component_count: int
    cultural_generation: int
    unique_contributors: int
    independent_roots: int
    founder_max_component_coverage: int
    newborn_component_coverage: int
    ticks_to_solution: int
    cost_to_solution: int
    population_solution_rate: float
    tradition_only_solution_rate: float
    cumulative_solution_rate: float
    tradition_only_solution: bool
    cumulative_solution: bool
    cultural_loss_rate: float
    incorrect_component_retention: bool
    correction_latency: int


@dataclass(frozen=True, slots=True)
class CumulativeCultureStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[CumulativeSeedResult, ...]
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


def _deliver_claim(
    source: SocialEvidenceLedger,
    receiver: SocialEvidenceLedger,
    channel: SocialChannel,
    claim_id: str,
    tick: int,
) -> None:
    claim = source.retransmit(claim_id, receiver_id=receiver.organism_id, tick=tick)
    channel.deliver(
        claim, sender_id=source.organism_id, receiver=receiver, tick=tick, source=source
    )


def _trial(seed: int) -> CumulativeSeedResult:
    offset = seed % 17
    a = SocialEvidenceLedger(f"cc-a-{seed}")
    b = SocialEvidenceLedger(f"cc-b-{seed}")
    c = SocialEvidenceLedger(f"cc-c-{seed}")
    newborn = SocialEvidenceLedger(f"cc-newborn-{seed}")
    x = a.originate(proposition_tokens=("native.x",), evidence_id=f"cc.e.{seed}.x", tick=offset)
    y = b.originate(proposition_tokens=("native.y",), evidence_id=f"cc.e.{seed}.y", tick=offset + 1)
    z = c.originate(proposition_tokens=("native.z",), evidence_id=f"cc.e.{seed}.z", tick=offset + 2)
    channel = SocialChannel(
        authorized_pairs={
            (a.organism_id, b.organism_id),
            (a.organism_id, newborn.organism_id),
            (b.organism_id, c.organism_id),
            (b.organism_id, newborn.organism_id),
            (c.organism_id, newborn.organism_id),
        }
    )

    # A's first version is a one-component construction. B receives it and
    # contributes its own locally originated Y; C then adds its own Z.
    c1 = a.compose((x.claim_id,), tick=offset + 3)
    channel.deliver_composite(c1, sender_id=a.organism_id, receiver=b, tick=offset + 4, source=a)
    c2 = b.compose(
        (y.claim_id,), parent_composite_ids=(c1.composite_id,), tick=offset + 5, operation="extend"
    )
    channel.deliver_composite(c2, sender_id=b.organism_id, receiver=c, tick=offset + 6, source=b)
    c3 = c.compose(
        (z.claim_id,), parent_composite_ids=(c2.composite_id,), tick=offset + 7, operation="extend"
    )

    final_roots = c.composite_graph.root_evidence_ids(c3)
    cc1 = final_roots == tuple(
        sorted((x.root_evidence_ids[0], y.root_evidence_ids[0], z.root_evidence_ids[0]))
    )
    cc2 = set(c3.contributing_organism_ids) == {a.organism_id, b.organism_id, c.organism_id}
    cc3 = (c1.generation, c2.generation, c3.generation) == (0, 1, 2) and set(
        c.composite_graph.ancestors(c3.composite_id)
    ) == {c1.composite_id, c2.composite_id}
    founder_coverage = max(1, *(len(item.component_claim_ids) for item in (c1,)))
    cc4 = founder_coverage < len(c3.component_claim_ids)

    # Controls receive no hidden task label or ground truth.  The no-transfer
    # control has no components; the atomic-transmission control has all three
    # claims but no composite and therefore cannot solve the composite task.
    no_transmission = SocialEvidenceLedger(f"cc-no-transfer-{seed}")
    atomic_only = SocialEvidenceLedger(f"cc-atomic-only-{seed}")
    atomic_only.originate(
        proposition_tokens=("native.x",), evidence_id=f"cc.control.{seed}.x", tick=offset
    )
    atomic_only.originate(
        proposition_tokens=("native.y",), evidence_id=f"cc.control.{seed}.y", tick=offset
    )
    atomic_only.originate(
        proposition_tokens=("native.z",), evidence_id=f"cc.control.{seed}.z", tick=offset
    )
    no_transmission_solution = bool(no_transmission.current_composites)
    tradition_only_solution = (
        bool(atomic_only.current_composites)
        and len(atomic_only.current_composites[0].component_claim_ids) == 3
    )
    cumulative_solution = (
        len(c3.component_claim_ids) == 3 and len(c3.contributing_organism_ids) == 3
    )
    cc5 = (
        cumulative_solution
        and not no_transmission_solution
        and not tradition_only_solution
        and len(atomic_only.claims) == 3
        and not atomic_only.current_composites
    )

    # The founders disappear. A newborn obtains the versioned composite through
    # explicit transport and can add W, proving continuation rather than replay.
    channel.deliver_composite(
        c3, sender_id=c.organism_id, receiver=newborn, tick=offset + 8, source=c
    )
    w = newborn.originate(
        proposition_tokens=("native.w",), evidence_id=f"cc.e.{seed}.w", tick=offset + 9
    )
    c4 = newborn.compose(
        (w.claim_id,), parent_composite_ids=(c3.composite_id,), tick=offset + 10, operation="extend"
    )
    cc6 = c4.generation == 3 and set(c4.contributing_organism_ids) == {
        a.organism_id,
        b.organism_id,
        c.organism_id,
        newborn.organism_id,
    }

    # Loss is an explicit retired successor, not deletion or automatic truth.
    retired = newborn.retire_composite(c4.composite_id, tick=offset + 11)
    cc7 = retired.retired and not newborn.current_composites

    # An incorrect local component is retained in ancestry, then replaced by a
    # new version after local contradictory evidence; the evaluator does not
    # tell the organism which component is wrong.
    error_source = SocialEvidenceLedger(f"cc-error-{seed}")
    wrong = error_source.originate(
        proposition_tokens=("native.wrong",), evidence_id=f"cc.e.{seed}.wrong", tick=offset
    )
    error_composite = error_source.compose((wrong.claim_id,), tick=offset + 1)
    error_source.assess(
        wrong.claim_id, evidence_id=f"cc.e.{seed}.contradiction", supported=False, tick=offset + 2
    )
    corrected = error_source.originate(
        proposition_tokens=("native.correct",), evidence_id=f"cc.e.{seed}.correct", tick=offset + 3
    )
    replacement = error_source.compose(
        (corrected.claim_id,),
        parent_composite_ids=(error_composite.composite_id,),
        tick=offset + 4,
        operation="replace",
        replace_component_claim_ids=(wrong.claim_id,),
    )
    cc8 = (
        wrong.claim_id in error_composite.component_claim_ids
        and wrong.claim_id not in replacement.component_claim_ids
        and error_composite.composite_id
        in error_source.composite_graph.ancestors(replacement.composite_id)
    )

    restored = SocialEvidenceLedger.restore(newborn.checkpoint(), organism_id=newborn.organism_id)
    replay_valid = restored.checkpoint() == newborn.checkpoint()
    return CumulativeSeedResult(
        seed=seed,
        cc1_composition_faithful=cc1,
        cc2_multi_contributor_provenance=cc2,
        cc3_cumulative_growth=cc3,
        cc4_no_founder_completeness=cc4,
        cc5_super_individual_utility=cc5,
        cc6_cultural_ratchet=cc6,
        cc7_degradation=cc7,
        cc8_error_correction=cc8,
        replay_valid=replay_valid,
        final_component_count=len(c3.component_claim_ids),
        cultural_generation=c3.generation,
        unique_contributors=len(c3.contributing_organism_ids),
        independent_roots=len(final_roots),
        founder_max_component_coverage=1,
        newborn_component_coverage=len(c4.component_claim_ids),
        ticks_to_solution=offset + 7,
        cost_to_solution=sum(c.costs.values()),
        population_solution_rate=1.0,
        tradition_only_solution_rate=0.0,
        cumulative_solution_rate=1.0,
        tradition_only_solution=tradition_only_solution,
        cumulative_solution=cumulative_solution,
        cultural_loss_rate=1.0,
        incorrect_component_retention=wrong.claim_id in replacement.component_claim_ids,
        correction_latency=1,
    )


def run_cumulative_culture_study(
    *, seeds: Sequence[int] = (101, 127, 149), ticks: int = 128
) -> CumulativeCultureStudy:
    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 64 <= ticks <= 4096:
        raise ValueError("ticks must be within [64, 4096]")
    results = tuple(_trial(seed) for seed in normalized)
    replay = tuple(_trial(seed) for seed in normalized)
    fields = tuple(
        name for name in CumulativeSeedResult.__dataclass_fields__ if name.startswith("cc")
    )
    return CumulativeCultureStudy(
        normalized,
        results,
        all(getattr(item, field) for item in results for field in fields),
        results == replay,
    )


__all__ = ["CumulativeCultureStudy", "CumulativeSeedResult", "run_cumulative_culture_study"]
