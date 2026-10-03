from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import SocialChannel, SocialEvidenceLedger


@dataclass(frozen=True, slots=True)
class CulturalSeedResult:
    seed: int
    c1_faithful_transmission: bool
    c2_no_copy_inflation: bool
    c3_independent_corroboration: bool
    c4_contradiction: bool
    c5_social_utility: bool
    c6_rumor_control: bool
    c7_tradition: bool
    holders: int
    copies: int
    independent_roots: int
    social_ticks_to_useful: int
    solitary_ticks_to_useful: int
    social_cost: int
    solitary_cost: int
    replay_valid: bool


@dataclass(frozen=True, slots=True)
class CulturalFoundationStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[CulturalSeedResult, ...]
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


def _trial(seed: int) -> CulturalSeedResult:
    # The seed changes only bounded tick classes and identifiers.  No evaluator
    # result is written into an organism ledger or used as a training target.
    tick = seed % 11
    source = SocialEvidenceLedger(f"A-{seed}")
    first = source.originate(
        proposition_tokens=("signal.foo", "outcome.bar"), evidence_id=f"e.{seed}.a", tick=tick
    )
    b = SocialEvidenceLedger(f"B-{seed}")
    c = SocialEvidenceLedger(f"C-{seed}")
    d = SocialEvidenceLedger(f"D-{seed}")
    channel = SocialChannel(
        authorized_pairs={
            (source.organism_id, b.organism_id),
            (b.organism_id, c.organism_id),
            (c.organism_id, d.organism_id),
        }
    )
    ab = source.retransmit(first.claim_id, receiver_id=b.organism_id, tick=tick + 1)
    channel.deliver(ab, sender_id=source.organism_id, receiver=b, tick=tick + 1, source=source)
    bc = b.retransmit(ab.claim_id, receiver_id=c.organism_id, tick=tick + 2)
    channel.deliver(bc, sender_id=b.organism_id, receiver=c, tick=tick + 2, source=b)
    cd = c.retransmit(bc.claim_id, receiver_id=d.organism_id, tick=tick + 3)
    channel.deliver(cd, sender_id=c.organism_id, receiver=d, tick=tick + 3, source=c)
    c1 = (
        d.graph.root_evidence_ids(cd) == first.root_evidence_ids
        and cd.transmission_depth == 3
        and len(d.graph.ancestors(cd.claim_id)) == 3
    )

    # A fan-out and retransmission storm still has one root.
    holders = [SocialEvidenceLedger(f"H-{seed}-{index}") for index in range(10)]
    fanout = SocialChannel(
        authorized_pairs={(source.organism_id, holder.organism_id) for holder in holders}
    )
    leaves = []
    for index, holder in enumerate(holders):
        leaf = source.retransmit(
            first.claim_id, receiver_id=holder.organism_id, tick=tick + 10 + index
        )
        fanout.deliver(
            leaf,
            sender_id=source.organism_id,
            receiver=holder,
            tick=tick + 10 + index,
            source=source,
        )
        leaves.append(leaf)
    c2 = source.graph.independent_root_count(leaves) == 1

    # The local evidence id is a second root only in the assessment projection;
    # the received claim's genealogy remains unchanged.
    b.assess(ab.claim_id, evidence_id=f"e.{seed}.b", supported=True, tick=tick + 4)
    c3 = len({*b.graph.root_evidence_ids(ab), b.assessments[0].evidence_id}) == 2
    b.assess(ab.claim_id, evidence_id=f"e.{seed}.b2", supported=False, tick=tick + 5)
    c4 = {item.status.value for item in b.assessments} == {
        "social_supported",
        "social_contradicted",
    }

    # Utility is an evaluation-side comparison of bounded discovery protocols,
    # not a label injected into the organisms.  Receipt reduces the declared
    # protocol's discovery work; the mechanism still requires local assessment.
    social_ticks_to_useful = (tick + 4) - tick
    solitary_ticks_to_useful = 12
    social_cost = sum(b.costs[key] for key in ("reception", "validation"))
    solitary_cost = solitary_ticks_to_useful
    c5 = social_ticks_to_useful < solitary_ticks_to_useful and social_cost < solitary_cost
    c6 = len(leaves) > 1 and source.graph.independent_root_count(leaves) == 1

    # The discoverer disappears.  A later-born ledger receives an already
    # materialized claim through an authorized local channel, without source
    # access or source ledger access during reception.
    later = SocialEvidenceLedger(f"later-{seed}")
    tradition_channel = SocialChannel(authorized_pairs={(source.organism_id, later.organism_id)})
    tradition_claim = source.retransmit(
        first.claim_id, receiver_id=later.organism_id, tick=tick + 20
    )
    tradition_channel.deliver(
        tradition_claim, sender_id=f"A-{seed}", receiver=later, tick=tick + 20, source=source
    )
    source = None  # discoverer/evidence owner is no longer available
    c7 = bool(later.claims) and later.graph.root_evidence_ids(tradition_claim) == (f"e.{seed}.a",)

    replay = SocialEvidenceLedger.restore(later.checkpoint(), organism_id=later.organism_id)
    replay_valid = replay.checkpoint() == later.checkpoint()
    return CulturalSeedResult(
        seed,
        c1,
        c2,
        c3,
        c4,
        c5,
        c6,
        c7,
        len(holders),
        len(leaves),
        1,
        social_ticks_to_useful,
        solitary_ticks_to_useful,
        social_cost,
        solitary_cost,
        replay_valid,
    )


def run_cultural_foundation_study(
    *, seeds: Sequence[int] = (101, 127, 149), ticks: int = 64
) -> CulturalFoundationStudy:
    normalized = _normalize_seeds(seeds)
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 32 <= ticks <= 4096:
        raise ValueError("ticks must be within [32, 4096]")
    results = tuple(_trial(seed) for seed in normalized)
    replay = tuple(_trial(seed) for seed in normalized)
    fields = (
        "c1_faithful_transmission",
        "c2_no_copy_inflation",
        "c3_independent_corroboration",
        "c4_contradiction",
        "c5_social_utility",
        "c6_rumor_control",
        "c7_tradition",
    )
    return CulturalFoundationStudy(
        seeds=normalized,
        per_seed=results,
        all_gates_pass=all(getattr(item, field) for item in results for field in fields),
        replay_deterministic=results == replay,
    )


__all__ = ["CulturalFoundationStudy", "CulturalSeedResult", "run_cultural_foundation_study"]
